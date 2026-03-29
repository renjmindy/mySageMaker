# Canvas API Patterns, Animation Frame Handling & Collision Detection

## Canvas API Patterns

### Context Acquisition and Guards

Always guard against missing 2D context — some browsers or environments may return `null`.

```js
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
if (!ctx) {
  console.error('Canvas 2D context unavailable');
  return; // exit gracefully, do not start loop
}
```

### Pixel-Perfect Canvas Sizing

Match canvas logical size to CSS size and account for device pixel ratio to avoid blurry rendering on HiDPI screens.

```js
function resizeCanvas(canvas, ctx) {
  const dpr = window.devicePixelRatio || 1;
  const w = window.innerWidth;
  const h = window.innerHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.scale(dpr, dpr);
}
```

Call `resizeCanvas` once at init and again inside the `resize` event listener.

### Clear Strategy

Use `clearRect` over `fillRect` for clearing — it's faster when the canvas background is transparent or handled by a background blit.

```js
// Good — fast clear
ctx.clearRect(0, 0, canvas.width, canvas.height);

// Only use fillRect if you need a solid colour clear and have no background blit
ctx.fillStyle = '#87CEEB';
ctx.fillRect(0, 0, canvas.width, canvas.height);
```

For games with a static background, skip `clearRect` entirely and blit the pre-rendered background instead — it clears and redraws in one call.

```js
ctx.drawImage(bgCanvas, 0, 0); // clears + redraws background in one operation
```

### Offscreen Canvas for Static Content

Pre-render anything that doesn't change frame-to-frame to an offscreen canvas at init.

```js
function buildBackground(width, height) {
  const offscreen = document.createElement('canvas');
  offscreen.width = width;
  offscreen.height = height;
  const octx = offscreen.getContext('2d');
  // draw sky, ground texture, sketchy lines, etc.
  drawSketchyBackground(octx, width, height);
  return offscreen; // store reference, blit each frame
}
```

Rebuild the offscreen canvas on viewport resize.

### Z-Order Draw Calls

Always draw in explicit z-order. Never rely on insertion order of objects in arrays. Document the draw order as a comment at the top of the render function.

```js
function render(ctx, state, canvas, now) {
  // Z-order:
  // 1. Background blit
  // 2. Far cloud layer
  // 3. Near cloud layer
  // 4. Pipes
  // 5. Particle trail
  // 6. Ghosty sprite
  // 7. Score popups
  // 8. Score bar
  // 9. State overlay (MENU / PAUSED / GAME_OVER)
  // 10. Collision animation (flash / shake — topmost)
  ctx.drawImage(bgCanvas, 0, 0);
  renderClouds(ctx, state.clouds[0]);
  renderClouds(ctx, state.clouds[1]);
  renderPipes(ctx, state.pipes);
  renderParticles(ctx, state.particles, now);
  renderGhosty(ctx, state.ghosty, ghostyImg, now);
  renderScorePopups(ctx, state.scorePopups, now);
  renderScoreBar(ctx, state, canvas);
  renderOverlay(ctx, state, canvas, now);
  renderCollisionAnim(ctx, state, canvas, now);
}
```

### Transforms and State Isolation

Wrap any draw call that uses transforms in `save`/`restore`. Never leave a dirty transform on the context.

```js
function renderGhosty(ctx, ghosty, img, now) {
  const angle = Math.min(Math.max(ghosty.vy / 600, -0.4), 0.8); // clamp rotation
  ctx.save();
  ctx.translate(ghosty.x + SPRITE_W / 2, ghosty.y + SPRITE_H / 2);
  ctx.rotate(angle);
  ctx.drawImage(img, -SPRITE_W / 2, -SPRITE_H / 2, SPRITE_W, SPRITE_H);
  ctx.restore();
}
```

### Alpha Batching

Set `globalAlpha` once per group, not per element. Reset to `1` after the group.

```js
// Good — one alpha set per layer
ctx.globalAlpha = 0.6;
for (const cloud of farLayer) drawCloud(ctx, cloud);
ctx.globalAlpha = 0.85;
for (const cloud of nearLayer) drawCloud(ctx, cloud);
ctx.globalAlpha = 1;
```

### Text Rendering

Cache font strings as constants. Avoid template literals inside the render loop for font assignment.

```js
const FONT_SCORE = '28px monospace';
const FONT_TITLE = 'bold 48px monospace';

// In render — no string allocation
ctx.font = FONT_SCORE;
ctx.fillText(String(state.score), x, y);
```

Use `ctx.textAlign` and `ctx.textBaseline` explicitly before every text draw — never assume they carry over from a previous frame.

---

## Animation Frame Handling

### Single RAF Loop

Use exactly one `requestAnimationFrame` loop for the entire game. Never nest RAF calls or run multiple loops simultaneously.

```js
let rafId;

function gameLoop(timestamp) {
  update(timestamp);
  render(timestamp);
  rafId = requestAnimationFrame(gameLoop);
}

// Start
rafId = requestAnimationFrame(gameLoop);

// Stop (only for full teardown, not for pause)
cancelAnimationFrame(rafId);
```

### Timestamp Handling

The `timestamp` passed by RAF is a `DOMHighResTimeStamp` in milliseconds with sub-millisecond precision. Always use it — never use `Date.now()` inside the game loop.

```js
function gameLoop(timestamp) {
  const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05); // seconds, capped
  state.lastTimestamp = timestamp;
  // ...
}
```

Initialise `lastTimestamp` to `0` in state. On the very first frame, `dt` will be large — the `0.05` cap handles this safely.

### Pause Without Cancelling RAF

Keep the loop running during pause. Gate gameplay systems behind a state check. This keeps the renderer and cloud animation active.

```js
function gameLoop(timestamp) {
  const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05);
  state.lastTimestamp = timestamp;

  updateClouds(state, canvas.width, dt); // always runs

  if (state.gameState === 'PLAYING') {
    updatePhysics(state, dt);
    updatePipes(state, canvas.width, canvas.height, dt);
    checkCollisions(state, timestamp, canvas.height);
    checkScoring(state);
    emitParticle(state, timestamp);
    updateParticles(state, timestamp);
    updateScorePopups(state, timestamp);
  }

  render(ctx, state, canvas, timestamp); // always runs
  requestAnimationFrame(gameLoop);
}
```

### Visibility Change Handling

When the tab is hidden, RAF stops firing. On resume, the next `timestamp` will be far in the future, producing a huge `dt`. The `0.05` cap handles this, but also reset `lastTimestamp` on visibility restore to avoid a single large jump.

```js
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (state.gameState === 'PLAYING') pauseGame();
  } else {
    state.lastTimestamp = 0; // force dt reset on next frame
  }
});
```

### Frame Budget Awareness

Target 60 FPS = ~16.67ms per frame. Keep all per-frame work well under 16ms. Rough budget:

| System | Budget |
|---|---|
| Physics + collision | ~1ms |
| Pipe + cloud update | ~1ms |
| Particle update | ~1ms |
| Background blit | ~1ms |
| Pipe rendering | ~2ms |
| Ghosty sprite | ~1ms |
| Particle trail render | ~3ms |
| UI / overlays | ~1ms |
| Headroom | ~5ms |

Use `performance.now()` during development to profile individual systems if frame rate drops.

---

## Efficient Collision Detection

### Choose the Right Primitive

Match the collision shape to the visual shape. Simpler shapes = faster tests.

| Shape pair | Test cost | Use when |
|---|---|---|
| AABB vs AABB | Very fast | Rectangular sprites, tiles |
| Circle vs AABB | Fast | Round sprites vs rectangular obstacles |
| Circle vs Circle | Very fast | Two round sprites |
| OBB vs OBB | Slow | Rotated rectangles (avoid in hot path) |

For Flappy Kiro: Ghosty uses a **circle** hitbox (feels fairer for a round ghost), pipes use **AABB**.

### Circle vs AABB (Nearest-Point Test)

The canonical O(1) circle-rectangle overlap test. Clamp the circle centre to the rectangle bounds, then check distance.

```js
function circleOverlapsRect(cx, cy, r, rect) {
  const nearestX = Math.max(rect.x, Math.min(cx, rect.x + rect.w));
  const nearestY = Math.max(rect.y, Math.min(cy, rect.y + rect.h));
  const dx = cx - nearestX;
  const dy = cy - nearestY;
  return (dx * dx + dy * dy) <= r * r; // avoid sqrt — compare squared distances
}
```

Always compare squared distances. `Math.sqrt` is expensive and unnecessary for overlap tests.

### Derive Hitbox on Demand

Don't store hitbox coordinates on the entity — derive them from position each frame. This avoids stale hitbox bugs when entities move.

```js
function getCircleHitbox(ghosty, spriteW, spriteH, inset) {
  return {
    cx: ghosty.x + spriteW / 2,
    cy: ghosty.y + spriteH / 2,
    r: Math.min(spriteW, spriteH) / 2 - inset,
  };
}

// Pipe rects derived on demand from gapCenterY
function getPipeRects(pipe, gapSize, pipeWidth, canvasHeight) {
  return {
    top:    { x: pipe.x, y: 0,                          w: pipeWidth, h: pipe.gapCenterY - gapSize / 2 },
    bottom: { x: pipe.x, y: pipe.gapCenterY + gapSize / 2, w: pipeWidth, h: canvasHeight - (pipe.gapCenterY + gapSize / 2) },
  };
}
```

### Broad Phase Before Narrow Phase

For scenes with many objects, skip expensive narrow-phase tests using a cheap broad-phase check first.

```js
function checkCollisions(state, now, canvasHeight) {
  if (now < state.invincibleUntil) return; // invincibility guard — earliest exit

  const { cx, cy, r } = getCircleHitbox(state.ghosty, SPRITE_W, SPRITE_H, HITBOX_INSET);

  for (const pipe of state.pipes) {
    // Broad phase: is ghosty even in the x-range of this pipe?
    if (cx + r < pipe.x || cx - r > pipe.x + PIPE_WIDTH) continue;

    // Narrow phase: circle vs top and bottom rects
    const { top, bottom } = getPipeRects(pipe, GAP_SIZE, PIPE_WIDTH, canvasHeight);
    if (circleOverlapsRect(cx, cy, r, top) || circleOverlapsRect(cx, cy, r, bottom)) {
      triggerCollision(state, now);
      return;
    }
  }

  // Boundary checks — simple threshold comparisons, no shape test needed
  if (cy + r >= canvasHeight - SCORE_BAR_H) { triggerCollision(state, now); return; }
  if (cy - r <= 0)                           { triggerCollision(state, now); return; }
}
```

### Early Exit on First Hit

Return immediately after the first collision is detected. There's no benefit to checking remaining objects once a collision is confirmed.

### Invincibility Guard as First Check

Always check the invincibility window before any shape test. It's a single comparison and avoids all subsequent work.

```js
if (now < state.invincibleUntil) return;
```

### Avoid Collision Detection When Not Playing

Gate the entire collision check behind the game state. Don't run collision logic during MENU, PAUSED, or GAME_OVER.

```js
// In game loop
if (state.gameState === 'PLAYING') {
  checkCollisions(state, timestamp, canvas.height);
}
```

### Scoring as a Separate Pass

Scoring (did Ghosty pass the pipe midpoint?) is not a collision — it's a positional check. Keep it in a separate `checkScoring` function, not inside `checkCollisions`. This keeps each function's responsibility clear and avoids mixing hit detection with score logic.

```js
function checkScoring(state) {
  for (const pipe of state.pipes) {
    if (!pipe.scored && state.ghosty.x > pipe.x + PIPE_WIDTH / 2) {
      pipe.scored = true;
      state.score++;
      // ... spawn popup, play sound, check milestone
    }
  }
}
```
