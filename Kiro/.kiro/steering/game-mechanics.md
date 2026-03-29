# Flappy Kiro — Game Mechanics Reference

This file documents the specific physics constants, movement algorithms, and collision geometry for Flappy Kiro. All values come from `game-config.json` — never hardcode them in `game.js`.

---

## Physics Constants

All values are sourced from `game-config.json` at runtime. The table below documents their purpose and tuning rationale.

| Config key | Value | Unit | Purpose |
|---|---|---|---|
| `physics.gravity` | `800` | px/s² | Downward acceleration applied every frame |
| `physics.jumpVelocity` | `-300` | px/s | Upward velocity impulse on flap (negative = up) |
| `physics.terminalVelocity` | `600` | px/s | Maximum downward speed — prevents infinite acceleration |
| `pipes.wallSpeed` | `120` | px/s | Initial pipe scroll speed at session start |
| `pipes.gapSize` | `140` | px | Fixed vertical gap between top and bottom pipe |
| `pipes.wallSpacing` | `350` | px | Horizontal distance between consecutive pipe pair spawn positions |
| `pipes.gapMargin` | `60` | px | Minimum distance from canvas top/bottom edge to gap edge |
| `pipes.speedIncrement` | `20` | px/s | Speed added to pipe scroll at each milestone |
| `pipes.speedMilestone` | `5` | score | Score interval at which speed increments |
| `pipes.maxWallSpeed` | `300` | px/s | Hard cap on pipe scroll speed |
| `collision.hitboxInset` | `8` | px | Pixels to shrink hitbox on each side vs sprite bounds |
| `collision.invincibilityMs` | `1500` | ms | Grace period at session start — no collisions trigger |
| `visual.particleDuration` | `500` | ms | Particle lifetime before expiry |
| `visual.scorePopupDuration` | `700` | ms | Score popup lifetime before expiry |
| `visual.collisionAnimMs` | `500` | ms | Total collision animation duration (flash + shake) |

### Tuning Notes

- Increasing `gravity` makes the game feel heavier and more punishing. Decreasing it makes Ghosty float.
- `jumpVelocity` and `gravity` are coupled — if you raise gravity, raise the magnitude of `jumpVelocity` proportionally to maintain the same arc height.
- `terminalVelocity` prevents the "death dive" feel on long falls. At `600 px/s` with a typical canvas height of ~700px, Ghosty reaches the ground in ~1.2s from the top — fast but readable.
- `gapMargin: 60` ensures the gap is never flush with the canvas edge. With `gapSize: 140`, the safe zone for `gapCenterY` is `[60 + 70, canvasHeight - scoreBarH - 60 - 70]`.

---

## Movement Algorithms

### Ghosty Physics Step

Applied once per frame while `gameState === 'PLAYING'`. Uses time-based integration so behaviour is consistent at any frame rate.

```js
function updatePhysics(state, dt) {
  const ghosty = state.ghosty;
  const { gravity, terminalVelocity } = cfg.physics;

  ghosty.prevY = ghosty.y;                                      // store for interpolation
  ghosty.vy = Math.min(ghosty.vy + gravity * dt, terminalVelocity); // integrate + clamp
  ghosty.y += ghosty.vy * dt;                                   // integrate position
  ghosty.y = Math.max(ghosty.y, 0);                             // ceiling clamp
}
```

Step-by-step for a single frame at 60 FPS (`dt ≈ 0.0167s`), starting from rest (`vy = 0`, `y = 350`):

```
vy_new = min(0 + 800 × 0.0167, 600) = min(13.36, 600) = 13.36 px/s
y_new  = 350 + 13.36 × 0.0167      = 350.22 px
```

After a flap (`vy = -300`):
```
vy_new = min(-300 + 800 × 0.0167, 600) = min(-286.64, 600) = -286.64 px/s
y_new  = 350 + (-286.64 × 0.0167)      = 345.21 px  (moving up)
```

### Flap Impulse

Flap replaces `vy` entirely — it does not add to it. This gives consistent arc height regardless of current velocity.

```js
function flap(state) {
  if (state.gameState !== 'PLAYING') return; // guard — ignored when paused
  state.ghosty.vy = cfg.physics.jumpVelocity; // -300 px/s
  audioManager.playSound(audioManager.sounds.jump);
}
```

### Render Interpolation

Ghosty's rendered position is interpolated between the previous and current physics positions to eliminate jitter at display refresh rates above or below 60 Hz.

```js
function getInterpolatedY(ghosty, alpha) {
  // alpha = time elapsed since last physics step / physics step duration
  // alpha ∈ [0, 1]
  return ghosty.prevY + (ghosty.y - ghosty.prevY) * alpha;
}
```

In the renderer, pass the sub-frame alpha derived from the RAF timestamp:

```js
// alpha approximation — for a fixed-step loop this is always ~1.0 at 60fps
// For variable-step (dt-based) loops, render at current position directly
const renderY = getInterpolatedY(state.ghosty, 1.0);
```

### Ghosty Sprite Rotation

Rotation angle is derived from `vy` and clamped to prevent extreme tilts. Positive `vy` (falling) → positive angle (nose down). Zero or negative `vy` (rising) → zero or negative angle (nose up/level).

```js
function getGhostyAngle(vy) {
  // Map vy range [-300, 600] to angle range [-0.4, 0.8] radians
  // Clamp to prevent over-rotation
  return Math.min(Math.max(vy / cfg.physics.terminalVelocity * 0.8, -0.4), 0.8);
}
```

| `vy` | Angle (rad) | Visual |
|---|---|---|
| `-300` (just flapped) | `-0.4` | Nose up ~23° |
| `0` (apex) | `0` | Level |
| `300` (mid-fall) | `0.4` | Nose down ~23° |
| `600` (terminal) | `0.8` | Nose down ~46° |

### Pipe Scrolling

All pipes share the same `pipeSpeed` from state. Speed is time-based.

```js
function updatePipes(state, canvasWidth, canvasHeight, dt) {
  const { wallSpeed: _, gapSize, wallSpacing, gapMargin } = cfg.pipes;
  const speed = state.pipeSpeed; // current speed (may be > wallSpeed after milestones)

  for (let i = state.pipes.length - 1; i >= 0; i--) {
    const pipe = state.pipes[i];
    pipe.x -= speed * dt;

    // Recycle pipes that have fully exited the left edge
    if (pipe.x + PIPE_WIDTH < 0) {
      pipePairPool.release(pipe);
      state.pipes.splice(i, 1);
    }
  }

  // Spawn new pipe when gap opens on the right
  const rightmost = state.pipes.reduce((max, p) => Math.max(max, p.x), 0);
  if (state.pipes.length === 0 || rightmost < canvasWidth - wallSpacing) {
    spawnPipe(state, canvasWidth, canvasHeight);
  }
}
```

### Speed Progression

Speed increments at every `speedMilestone` score, capped at `maxWallSpeed`.

```js
// Inside checkScoring, after incrementing state.score:
if (state.score % cfg.pipes.speedMilestone === 0) {
  state.pipeSpeed = Math.min(
    state.pipeSpeed + cfg.pipes.speedIncrement,
    cfg.pipes.maxWallSpeed
  );
}
```

Progression table (starting from `wallSpeed: 120`):

| Score | Pipe speed (px/s) |
|---|---|
| 0 | 120 |
| 5 | 140 |
| 10 | 160 |
| 35 | 260 |
| 45 | 300 (capped) |

---

## Collision Geometry

### Ghosty Hitbox Derivation

Ghosty uses a circular hitbox centred on the sprite, inset by `hitboxInset` pixels. This feels fairer than AABB for a round ghost sprite.

```js
function getCircleHitbox(ghosty, spriteW, spriteH) {
  const inset = cfg.collision.hitboxInset; // 8px
  return {
    cx: ghosty.x + spriteW / 2,
    cy: ghosty.y + spriteH / 2,
    r:  Math.min(spriteW, spriteH) / 2 - inset,
  };
}
```

For a 40×40 sprite at position `(200, 300)`:
```
cx = 200 + 20 = 220
cy = 300 + 20 = 320
r  = min(40, 40) / 2 - 8 = 20 - 8 = 12px
```

The hitbox is 12px radius — visually smaller than the sprite, giving the player a small margin of forgiveness.

### Pipe Rect Derivation

Pipe rectangles are derived on demand from `gapCenterY`. Never stored — always computed.

```js
function getPipeRects(pipe, canvasHeight) {
  const { gapSize } = cfg.pipes;
  const halfGap = gapSize / 2; // 70px
  return {
    top: {
      x: pipe.x,
      y: 0,
      w: PIPE_WIDTH,
      h: pipe.gapCenterY - halfGap,       // top of gap
    },
    bottom: {
      x: pipe.x,
      y: pipe.gapCenterY + halfGap,       // bottom of gap
      w: PIPE_WIDTH,
      h: canvasHeight - (pipe.gapCenterY + halfGap),
    },
  };
}
```

For `gapCenterY = 350`, `canvasHeight = 700`, `PIPE_WIDTH = 52`:
```
top rect:    { x: pipe.x, y: 0,   w: 52, h: 280 }   (350 - 70)
bottom rect: { x: pipe.x, y: 420, w: 52, h: 280 }   (700 - 420)
gap:         y 280 → 420, height exactly 140px ✓
```

### Gap Safe Zone

The `gapCenterY` for a new pipe is randomly chosen within the safe zone:

```
min = gapMargin + gapSize / 2         = 60 + 70  = 130px from top
max = canvasHeight - scoreBarH - gapMargin - gapSize / 2
    = 700 - 60 - 60 - 70             = 510px from top  (example at 700px height)
```

```js
function spawnPipe(state, canvasWidth, canvasHeight) {
  const { gapSize, gapMargin } = cfg.pipes;
  const SCORE_BAR_H = 50;
  const halfGap = gapSize / 2;
  const minY = gapMargin + halfGap;
  const maxY = canvasHeight - SCORE_BAR_H - gapMargin - halfGap;

  const pipe = pipePairPool.acquire();
  if (!pipe) return; // pool exhausted — skip spawn

  pipe.x = canvasWidth;
  pipe.gapCenterY = minY + Math.random() * (maxY - minY);
  pipe.scored = false;
  state.pipes.push(pipe);
}
```

### Circle vs AABB Test

```js
function circleOverlapsRect(cx, cy, r, rect) {
  // Clamp circle centre to nearest point on rect
  const nearestX = Math.max(rect.x, Math.min(cx, rect.x + rect.w));
  const nearestY = Math.max(rect.y, Math.min(cy, rect.y + rect.h));
  const dx = cx - nearestX;
  const dy = cy - nearestY;
  return dx * dx + dy * dy <= r * r; // squared distance — no sqrt needed
}
```

### Boundary Checks

Ground and ceiling are simple threshold comparisons — no shape test needed.

```js
// Ground: bottom of hitbox circle reaches score bar top
if (cy + r >= canvasHeight - SCORE_BAR_H) { triggerCollision(state, now); return; }

// Ceiling: top of hitbox circle reaches canvas top
if (cy - r <= 0) { triggerCollision(state, now); return; }
```

### Full Collision Check Order

```js
function checkCollisions(state, now, canvasHeight) {
  // 1. Invincibility guard — cheapest check, always first
  if (now < state.invincibleUntil) return;

  const { cx, cy, r } = getCircleHitbox(state.ghosty, SPRITE_W, SPRITE_H);

  // 2. Pipe collisions — broad phase x-range check before narrow circle-AABB
  for (const pipe of state.pipes) {
    if (cx + r < pipe.x || cx - r > pipe.x + PIPE_WIDTH) continue; // broad phase skip
    const { top, bottom } = getPipeRects(pipe, canvasHeight);
    if (circleOverlapsRect(cx, cy, r, top) || circleOverlapsRect(cx, cy, r, bottom)) {
      triggerCollision(state, now);
      return; // early exit on first hit
    }
  }

  // 3. Boundary checks — always last, no broad phase needed
  if (cy + r >= canvasHeight - SCORE_BAR_H) { triggerCollision(state, now); return; }
  if (cy - r <= 0)                           { triggerCollision(state, now); return; }
}
```

### Invincibility Window

Set at the start of each session. Lasts `1500ms`. Prevents any collision from triggering during the initial drop.

```js
// In startGame():
state.invincibleUntil = performance.now() + cfg.collision.invincibilityMs; // now + 1500ms
```

The guard in `checkCollisions` is a single timestamp comparison — `O(1)`, no shape work done.

---

## Scoring System

### Full checkScoring Implementation

`checkScoring` runs once per frame while `gameState === 'PLAYING'`. It iterates all active pipes, awards a point when Ghosty's x crosses the pipe midpoint, and applies speed progression at milestones.

```js
function checkScoring(state) {
  for (const pipe of state.pipes) {
    // Award point when Ghosty's leading edge passes the pipe centre
    if (!pipe.scored && state.ghosty.x > pipe.x + PIPE_WIDTH / 2) {
      pipe.scored = true;       // prevent double-counting on subsequent frames
      state.score++;

      spawnScorePopup(state, performance.now());
      audioManager.playSound(audioManager.sounds.score);

      // Speed milestone — only on exact multiples, never at score 0
      if (state.score % cfg.pipes.speedMilestone === 0) {
        state.pipeSpeed = Math.min(
          state.pipeSpeed + cfg.pipes.speedIncrement,
          cfg.pipes.maxWallSpeed
        );
      }
    }
  }
}
```

Key invariants:
- `pipe.scored` is set to `false` in `spawnPipe` and never reset mid-session — each pipe awards at most one point
- Score is never decremented — only `triggerCollision` ends a run
- Speed increment is applied immediately in the same frame the score changes — pipes speed up on the very next `updatePipes` call

### Score Popup Lifecycle

A `ScorePopup` is spawned on every score increment and expires after `scorePopupDuration` ms.

```js
function spawnScorePopup(state, now) {
  const popup = scorePopupPool.acquire();
  if (!popup) return; // pool exhausted — skip, don't block scoring

  popup.x = state.ghosty.x + SPRITE_W / 2; // centred on Ghosty
  popup.y = state.ghosty.y - 20;            // slightly above sprite
  popup.born = now;
  popup.duration = cfg.visual.scorePopupDuration; // 700ms
  state.scorePopups.push(popup);
}

function updateScorePopups(state, now) {
  for (let i = state.scorePopups.length - 1; i >= 0; i--) {
    if (now - state.scorePopups[i].born >= state.scorePopups[i].duration) {
      scorePopupPool.release(state.scorePopups[i]);
      state.scorePopups.splice(i, 1);
    }
  }
}
```

Rendering a popup — translate upward and fade out over its lifetime:

```js
function renderScorePopups(ctx, popups, now) {
  ctx.textAlign = 'center';
  ctx.font = '20px monospace';
  for (const popup of popups) {
    const t = (now - popup.born) / popup.duration; // 0 → 1
    const alpha = 1 - t;
    const offsetY = t * 30; // float up 30px over lifetime
    ctx.globalAlpha = alpha;
    ctx.fillStyle = '#ffffff';
    ctx.fillText('+1', popup.x, popup.y - offsetY);
  }
  ctx.globalAlpha = 1;
}
```

---

## Idle Float Animation (MENU State)

While `gameState === 'MENU'`, Ghosty bobs up and down using a sine wave driven by the RAF timestamp. No physics runs — this is purely a render-time calculation.

```js
function getIdleFloatY(baseY, now) {
  // Oscillate ±12px around baseY with a 1.8s period
  return baseY + Math.sin(now / 1800 * Math.PI * 2) * 12;
}
```

Usage in the renderer:

```js
function renderGhosty(ctx, ghosty, img, now, gameState) {
  let renderY = ghosty.y;

  if (gameState === 'MENU') {
    renderY = getIdleFloatY(canvas.height / 2 - SPRITE_H / 2, now);
    // No rotation during idle float
    ctx.drawImage(img, ghosty.x, renderY, SPRITE_W, SPRITE_H);
    return;
  }

  // PLAYING / PAUSED / GAME_OVER — use physics position with rotation
  const angle = getGhostyAngle(ghosty.vy);
  ctx.save();
  ctx.translate(ghosty.x + SPRITE_W / 2, renderY + SPRITE_H / 2);
  ctx.rotate(angle);
  ctx.drawImage(img, -SPRITE_W / 2, -SPRITE_H / 2, SPRITE_W, SPRITE_H);
  ctx.restore();
}
```

The float animation runs continuously because the renderer always fires regardless of game state — no special timer or interval needed.
