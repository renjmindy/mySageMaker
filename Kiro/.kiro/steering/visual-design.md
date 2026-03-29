# Visual Design: Sprite Rendering, Animation & Particle Effects

All visual values come from `game-config.json` and `ghosty-sprites.md`. Never hardcode colours, sizes, or durations in render functions.

---

## Sprite Rendering

### Ghosty Sprite Dimensions

The source sprite is 32×32px. It is rendered at **2× scale (64×64px)** on canvas for visibility.

```js
const SPRITE_SRC_W = 32;
const SPRITE_SRC_H = 32;
const SPRITE_W = 64;  // rendered width (2×)
const SPRITE_H = 64;  // rendered height (2×)
```

### Loading with Silent Fallback

```js
function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null); // null = use fallback
    img.src = src;
  });
}
```

### Drawing Ghosty with Rotation

Always wrap in `save`/`restore`. Translate to sprite centre, rotate, draw offset by half dimensions.

```js
function renderGhosty(ctx, ghosty, img, vy, gameState, now) {
  const cx = ghosty.x + SPRITE_W / 2;
  const cy = ghosty.y + SPRITE_H / 2;

  ctx.save();
  ctx.translate(cx, cy);

  if (gameState === 'PLAYING' || gameState === 'PAUSED') {
    // Rotation: clamp vy to angle range [-0.4, 0.8] radians
    const angle = Math.min(Math.max(vy / 600 * 0.8, -0.4), 0.8);
    ctx.rotate(angle);
  }
  // MENU and GAME_OVER: no rotation

  if (img) {
    ctx.drawImage(img, -SPRITE_W / 2, -SPRITE_H / 2, SPRITE_W, SPRITE_H);
  } else {
    // Fallback: white filled circle
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(0, 0, SPRITE_W / 2, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}
```

### Invincibility Flash

During the invincibility window at session start, Ghosty flashes by toggling `globalAlpha` at 100ms intervals.

```js
function getInvincibilityAlpha(now, invincibleUntil) {
  if (now >= invincibleUntil) return 1; // window expired — fully opaque
  // Toggle between 1.0 and 0.4 every 100ms
  return Math.floor(now / 100) % 2 === 0 ? 1.0 : 0.4;
}

// In renderGhosty, before ctx.save():
ctx.globalAlpha = getInvincibilityAlpha(now, state.invincibleUntil);
// ... draw sprite ...
ctx.globalAlpha = 1;
```

### Spritesheet Frame Animation

The current `ghosty.png` is a single frame. When the full spritesheet is available (96×64px), use `drawImage` with source rect to select frames.

```js
// Spritesheet layout: 3 cols × 2 rows, each cell 32×32px
// Row 0: Idle/Flap frames (col 0, col 1)
// Row 1: Death frames (col 0, col 1, col 2)

function getSpriteFrame(gameState, now) {
  if (gameState === 'MENU') {
    // Idle: alternate frames 0 and 1 every 400ms
    const frame = Math.floor(now / 400) % 2;
    return { sx: frame * 32, sy: 0, sw: 32, sh: 32 };
  }
  if (gameState === 'PLAYING') {
    // Flap: alternate frames 0 and 1 every 100ms
    const frame = Math.floor(now / 100) % 2;
    return { sx: frame * 32, sy: 0, sw: 32, sh: 32 };
  }
  // GAME_OVER / PAUSED: hold on frame 0
  return { sx: 0, sy: 0, sw: 32, sh: 32 };
}

// Usage (when spritesheet is available):
const { sx, sy, sw, sh } = getSpriteFrame(state.gameState, now);
ctx.drawImage(img, sx, sy, sw, sh, -SPRITE_W / 2, -SPRITE_H / 2, SPRITE_W, SPRITE_H);
```

---

## Pipe Visual Style

Pipes are solid green rectangles with a darker green cap on the open end (the end facing the gap).

```js
const PIPE_COLOR     = '#4CAF50'; // main body
const PIPE_CAP_COLOR = '#388E3C'; // darker cap
const PIPE_WIDTH     = 52;        // px
const PIPE_CAP_H     = 12;        // px — cap height

function renderPipes(ctx, pipes, canvasHeight, gapSize) {
  for (const pipe of pipes) {
    const halfGap = gapSize / 2;
    const topH    = pipe.gapCenterY - halfGap;
    const botY    = pipe.gapCenterY + halfGap;
    const botH    = canvasHeight - botY;

    // Top pipe body
    ctx.fillStyle = PIPE_COLOR;
    ctx.fillRect(pipe.x, 0, PIPE_WIDTH, topH);
    // Top pipe cap (bottom edge of top pipe)
    ctx.fillStyle = PIPE_CAP_COLOR;
    ctx.fillRect(pipe.x - 2, topH - PIPE_CAP_H, PIPE_WIDTH + 4, PIPE_CAP_H);

    // Bottom pipe body
    ctx.fillStyle = PIPE_COLOR;
    ctx.fillRect(pipe.x, botY, PIPE_WIDTH, botH);
    // Bottom pipe cap (top edge of bottom pipe)
    ctx.fillStyle = PIPE_CAP_COLOR;
    ctx.fillRect(pipe.x - 2, botY, PIPE_WIDTH + 4, PIPE_CAP_H);
  }
}
```

---

## Particle System

### Data Model

```js
// Allocated at init via ParticlePool (max 60)
{ x: 0, y: 0, born: 0, duration: 0 }
// duration = cfg.visual.particleDuration (500ms)
```

### Emit

One particle emitted per frame while `gameState === 'PLAYING'`. Position is Ghosty's current centre.

```js
function emitParticle(state, now) {
  const p = particlePool.acquire();
  if (!p) return; // pool exhausted — skip silently

  p.x = state.ghosty.x + SPRITE_W / 2;
  p.y = state.ghosty.y + SPRITE_H / 2;
  p.born = now;
  p.duration = cfg.visual.particleDuration; // 500ms
  state.particles.push(p);
}
```

### Update (expire and recycle)

Iterate backwards to safely splice. Release expired particles back to pool.

```js
function updateParticles(state, now) {
  for (let i = state.particles.length - 1; i >= 0; i--) {
    if (now - state.particles[i].born >= state.particles[i].duration) {
      particlePool.release(state.particles[i]);
      state.particles.splice(i, 1);
    }
  }
}
```

### Render

Each particle is a small translucent circle. Opacity and radius shrink linearly over its lifetime.

```js
function renderParticles(ctx, particles, now) {
  for (const p of particles) {
    const t = (now - p.born) / p.duration; // 0 → 1
    const alpha = (1 - t) * 0.6;           // max 0.6 opacity, fades to 0
    const radius = (1 - t) * 5 + 2;        // shrinks from 7px to 2px

    ctx.globalAlpha = alpha;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}
```

---

## Cloud Rendering

Two parallax layers. Each cloud is a rounded rectangle or ellipse with opacity `< 1.0`.

```js
// Cloud layer speeds (px/s, time-based)
const CLOUD_SPEEDS = [0.3, 0.7]; // index 0 = far, index 1 = near

function initClouds(canvasWidth, canvasHeight) {
  return [
    Array.from({ length: 6 }, (_, i) => ({
      x: (canvasWidth / 6) * i + Math.random() * 80,
      y: 20 + Math.random() * (canvasHeight * 0.4),
      width: 80 + Math.random() * 60,
      height: 30 + Math.random() * 20,
      opacity: 0.3 + Math.random() * 0.35, // strictly < 1.0
    })),
    Array.from({ length: 5 }, (_, i) => ({
      x: (canvasWidth / 5) * i + Math.random() * 60,
      y: 30 + Math.random() * (canvasHeight * 0.35),
      width: 60 + Math.random() * 50,
      height: 25 + Math.random() * 15,
      opacity: 0.5 + Math.random() * 0.3, // strictly < 1.0
    })),
  ];
}

function updateClouds(state, canvasWidth, dt) {
  // Always runs regardless of gameState
  for (let layer = 0; layer < 2; layer++) {
    for (const cloud of state.clouds[layer]) {
      cloud.x -= CLOUD_SPEEDS[layer] * dt * 60; // convert to px/frame equivalent
      if (cloud.x + cloud.width < 0) {
        cloud.x = canvasWidth; // wrap to right edge
      }
    }
  }
}

function renderClouds(ctx, clouds) {
  for (let layer = 0; layer < 2; layer++) {
    for (const cloud of clouds[layer]) {
      ctx.globalAlpha = cloud.opacity;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.ellipse(
        cloud.x + cloud.width / 2,
        cloud.y + cloud.height / 2,
        cloud.width / 2,
        cloud.height / 2,
        0, 0, Math.PI * 2
      );
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
}
```

---

## Score Bar

Persistent across all game states. Rendered last in z-order before overlays.

```js
const SCORE_BAR_H  = 40;
const SCORE_BAR_BG = 'rgba(30, 30, 40, 0.85)';
const FONT_SCORE_BAR = 'bold 18px sans-serif';

function renderScoreBar(ctx, state, canvas) {
  const y = canvas.height - SCORE_BAR_H;

  ctx.fillStyle = SCORE_BAR_BG;
  ctx.fillRect(0, y, canvas.width, SCORE_BAR_H);

  ctx.fillStyle = '#ffffff';
  ctx.font = FONT_SCORE_BAR;

  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(`Score: ${state.score}`, 20, y + SCORE_BAR_H / 2);

  ctx.textAlign = 'right';
  ctx.fillText(`Best: ${state.highScore}`, canvas.width - 20, y + SCORE_BAR_H / 2);
}
```

---

## State Overlays

### MENU Overlay

```js
const FONT_TITLE  = '900 42px sans-serif';
const FONT_PROMPT = '400 16px sans-serif';
const FONT_BEST   = '700 24px sans-serif';

function renderMenuOverlay(ctx, state, canvas, now) {
  // Title
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ffffff';
  ctx.font = FONT_TITLE;
  ctx.shadowColor = 'rgba(0,0,0,0.6)';
  ctx.shadowBlur = 4;
  ctx.fillText('FLAPPY KIRO', canvas.width / 2, canvas.height * 0.28);
  ctx.shadowBlur = 0;

  // High score
  ctx.font = FONT_BEST;
  ctx.fillText(`Best: ${state.highScore}`, canvas.width / 2, canvas.height * 0.62);

  // Pulsing start prompt (opacity 0.5 → 1.0 over 1s)
  const pulse = 0.5 + 0.5 * Math.abs(Math.sin(now / 1000 * Math.PI));
  ctx.globalAlpha = pulse;
  ctx.font = FONT_PROMPT;
  ctx.fillText('Press SPACE or tap to play', canvas.width / 2, canvas.height * 0.75);
  ctx.globalAlpha = 1;
}
```

### PAUSED Overlay

```js
function renderPausedOverlay(ctx, state, canvas) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '700 36px sans-serif';
  ctx.fillText('PAUSED', canvas.width / 2, canvas.height * 0.45);

  ctx.font = FONT_PROMPT;
  ctx.fillText('Press ESC or P to resume', canvas.width / 2, canvas.height * 0.58);
}
```

### GAME_OVER Overlay

```js
function renderGameOverOverlay(ctx, state, canvas, now) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  ctx.font = '700 36px sans-serif';
  ctx.fillText('GAME OVER', canvas.width / 2, canvas.height * 0.32);

  ctx.font = '700 24px sans-serif';
  ctx.fillText(`Score: ${state.score}`,     canvas.width / 2, canvas.height * 0.44);
  ctx.fillText(`Best: ${state.highScore}`,  canvas.width / 2, canvas.height * 0.52);

  if (state.newBest) {
    ctx.fillStyle = '#FFD700'; // gold
    ctx.font = '700 22px sans-serif';
    ctx.fillText('✨ NEW BEST! ✨', canvas.width / 2, canvas.height * 0.60);
    ctx.fillStyle = '#ffffff';
  }

  // Pulsing restart prompt
  const pulse = 0.5 + 0.5 * Math.abs(Math.sin(now / 1000 * Math.PI));
  ctx.globalAlpha = pulse;
  ctx.font = FONT_PROMPT;
  ctx.fillText('Press SPACE or tap to restart', canvas.width / 2, canvas.height * 0.72);
  ctx.globalAlpha = 1;
}
```

---

## Sketchy Background

Pre-rendered once at init to an offscreen canvas. Blit each frame with a single `drawImage`.

```js
function buildBackground(width, height) {
  const offscreen = document.createElement('canvas');
  offscreen.width = width;
  offscreen.height = height;
  const octx = offscreen.getContext('2d');

  // Sky fill
  octx.fillStyle = '#87CEEB';
  octx.fillRect(0, 0, width, height);

  // Sketchy texture — random short strokes for hand-drawn feel
  octx.strokeStyle = 'rgba(255,255,255,0.08)';
  octx.lineWidth = 1;
  for (let i = 0; i < 200; i++) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    const len = 10 + Math.random() * 30;
    const angle = Math.random() * Math.PI * 2;
    octx.beginPath();
    octx.moveTo(x, y);
    octx.lineTo(x + Math.cos(angle) * len, y + Math.sin(angle) * len);
    octx.stroke();
  }

  return offscreen;
}
```

Rebuild on viewport resize:

```js
function onResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    resizeCanvas(canvas, ctx);
    bgCanvas = buildBackground(canvas.width, canvas.height); // rebuild
  }, 100);
}
```

---

## Typography Reference

| Use | Font string | Colour |
|---|---|---|
| Title | `'900 42px sans-serif'` | `#ffffff` + shadow |
| Game Over heading | `'700 36px sans-serif'` | `#ffffff` |
| Score values | `'700 24px sans-serif'` | `#ffffff` |
| Score bar | `'bold 18px sans-serif'` | `#ffffff` |
| Score popup "+1" | `'700 20px sans-serif'` | `#ffffff` |
| New Best | `'700 22px sans-serif'` | `#FFD700` |
| Prompts (pulsing) | `'400 16px sans-serif'` | `#ffffff` (alpha varies) |

Always set `ctx.textAlign` and `ctx.textBaseline` explicitly before every `fillText` call — never assume they carry over from a previous draw.
