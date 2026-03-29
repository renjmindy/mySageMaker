# Game Architecture Standards: Flappy Kiro

## Modular Systems

### One Responsibility Per System

Each system owns exactly one concern. Systems never call each other — they only read and write the shared `state` object. The game loop is the only orchestrator.

| System | Owns | Does NOT touch |
|---|---|---|
| `updatePhysics` | `ghosty.y`, `ghosty.vy`, `ghosty.prevY` | pipes, score, clouds |
| `updatePipes` | `state.pipes`, `state.pipeSpeed` | ghosty, score, particles |
| `checkCollisions` | `state.collisionAnim`, `state.highScore` | pipes x-position, score |
| `checkScoring` | `state.score`, `pipe.scored`, `state.pipeSpeed` | ghosty position, collisions |
| `emitParticle` / `updateParticles` | `state.particles` | everything else |
| `updateClouds` | `state.clouds` | everything else |
| `render` | canvas pixels only — reads state, writes nothing | state object |

### System Signatures

All systems follow the same signature pattern: `(state, ...contextArgs)`. Context args are immutable values like `dt`, `now`, `canvasWidth`, `canvasHeight` — never DOM references.

```js
// Physics
function updatePhysics(state, dt) { ... }

// Pipes
function updatePipes(state, canvasWidth, canvasHeight, dt) { ... }

// Collision
function checkCollisions(state, now, canvasHeight) { ... }

// Scoring
function checkScoring(state) { ... }

// Particles
function emitParticle(state, now) { ... }
function updateParticles(state, now) { ... }

// Clouds — always runs, ignores gameState internally
function updateClouds(state, canvasWidth, dt) { ... }

// Renderer — reads state, never writes it
function render(ctx, state, canvas, now) { ... }
```

### System Registration Order

The game loop calls systems in a fixed, documented order. This order is the single source of truth for update sequencing — never reorder without updating this comment block.

```js
function gameLoop(timestamp) {
  const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05);
  state.lastTimestamp = timestamp;

  // --- Always-on systems ---
  updateClouds(state, canvas.width, dt);

  // --- Gameplay systems (PLAYING only) ---
  if (state.gameState === 'PLAYING') {
    updatePhysics(state, dt);
    updatePipes(state, canvas.width, canvas.height, dt);
    checkCollisions(state, timestamp, canvas.height);
    checkScoring(state);
    emitParticle(state, timestamp);
    updateParticles(state, timestamp);
    updateScorePopups(state, timestamp);
  }

  // --- Renderer (always) ---
  render(ctx, state, canvas, timestamp);

  requestAnimationFrame(gameLoop);
}
```

---

## Event Handling Patterns

### Translate Events to Intent, Not Actions

Input handlers translate raw browser events into game intents. They never call game logic directly from inside the event callback — they call named action functions that check game state before acting.

```js
// Good — event → intent function → state-guarded action
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space') handleAction();
  if (e.code === 'Escape' || e.code === 'KeyP') handlePause();
});

canvas.addEventListener('pointerdown', () => handleAction());

// Intent functions check state before acting
function handleAction() {
  if (state.gameState === 'MENU')      return startGame();
  if (state.gameState === 'PLAYING')   return flap(state);
  if (state.gameState === 'GAME_OVER') return restartGame();
  // PAUSED → no-op
}

function handlePause() {
  if (state.gameState === 'PLAYING') return pauseGame();
  if (state.gameState === 'PAUSED')  return resumeGame();
}
```

### Register Listeners Once

All event listeners are registered once during initialisation. Never add or remove listeners during gameplay or inside the game loop.

```js
function initInput() {
  window.addEventListener('keydown', onKeyDown);
  canvas.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('resize', onResize);
  document.addEventListener('visibilitychange', onVisibilityChange);
}
```

### Prevent Default Selectively

Only call `e.preventDefault()` for keys that would otherwise scroll the page (Space, arrow keys). Don't blanket-prevent all keyboard events.

```js
function onKeyDown(e) {
  if (e.code === 'Space') {
    e.preventDefault(); // prevent page scroll
    handleAction();
  }
  if (e.code === 'Escape' || e.code === 'KeyP') handlePause();
}
```

### Pointer Events Over Mouse/Touch

Use `pointerdown` instead of separate `mousedown` and `touchstart` listeners. It handles mouse, touch, and stylus with one handler.

```js
canvas.addEventListener('pointerdown', onPointerDown);
// Not: canvas.addEventListener('mousedown', ...); canvas.addEventListener('touchstart', ...);
```

### Resize Handling

Debounce resize events to avoid thrashing canvas dimensions on every pixel of drag.

```js
let resizeTimer;
function onResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    resizeCanvas(canvas, ctx);
    rebuildBackground(); // rebuild offscreen canvas at new size
    rescalePositions(state, canvas); // scale ghosty/pipe positions proportionally
  }, 100);
}
```

---

## State Management

### Single State Object

All mutable game state lives in one flat object. No state is stored on individual entity objects beyond their own data fields. No state is stored in module-level variables outside of `state`.

```js
const state = {
  // Game flow
  gameState: 'MENU',       // 'MENU' | 'PLAYING' | 'PAUSED' | 'GAME_OVER'
  lastTimestamp: 0,

  // Scoring
  score: 0,
  highScore: 0,
  newBest: false,

  // Ghosty
  ghosty: { x: 0, y: 0, vy: 0, prevY: 0 },

  // Entities
  pipes: [],
  particles: [],
  scorePopups: [],
  clouds: [[], []],

  // Timing
  invincibleUntil: 0,

  // Animation
  collisionAnim: null,     // null | { startTime, phase: 'flash' | 'shake' }

  // Difficulty
  pipeSpeed: 0,
};
```

### State Transitions Through Named Functions Only

Never write `state.gameState = '...'` outside of the four transition functions. This makes all state changes traceable and testable.

```js
function startGame() {
  state.gameState = 'PLAYING';
  state.score = 0;
  state.newBest = false;
  state.pipeSpeed = cfg.pipes.wallSpeed;
  state.invincibleUntil = performance.now() + cfg.collision.invincibilityMs;
  state.pipes.length = 0;
  state.particles.length = 0;
  state.scorePopups.length = 0;
  state.ghosty.x = canvas.width * 0.3;
  state.ghosty.y = canvas.height / 2;
  state.ghosty.vy = 0;
  state.ghosty.prevY = state.ghosty.y;
  audioManager.playBgMusic();
}

function restartGame() {
  startGame(); // identical reset — restartGame is an alias for clarity
}

function pauseGame() {
  state.gameState = 'PAUSED';
  audioManager.pauseBgMusic();
}

function resumeGame() {
  state.gameState = 'PLAYING';
  state.lastTimestamp = 0; // reset dt to avoid jump on resume
  audioManager.playBgMusic();
}

function triggerCollision(state, now) {
  if (state.score > state.highScore) {
    state.highScore = state.score;
    state.newBest = true;
    writeHighScore(state.highScore);
  }
  state.collisionAnim = { startTime: now, phase: 'flash' };
  audioManager.playSound(audioManager.sounds.gameOver);
  audioManager.stopBgMusic();
  // gameState transitions to GAME_OVER when collisionAnim completes in renderer
}
```

### Collision Animation Drives GAME_OVER Transition

`triggerCollision` does not set `gameState` to `GAME_OVER` directly. The renderer drives this transition when the animation completes. This keeps the animation timing decoupled from the collision logic.

```js
function renderCollisionAnim(ctx, state, canvas, now) {
  if (!state.collisionAnim) return;

  const elapsed = now - state.collisionAnim.startTime;
  const total = cfg.visual.collisionAnimMs; // 500ms

  if (elapsed < total * 0.4) {
    // Flash phase — white overlay, fading
    ctx.globalAlpha = 1 - elapsed / (total * 0.4);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalAlpha = 1;
  } else if (elapsed < total) {
    // Shake phase — offset canvas transform
    const shakeAmt = 6 * (1 - (elapsed - total * 0.4) / (total * 0.6));
    const shakeX = (Math.random() - 0.5) * 2 * shakeAmt;
    const shakeY = (Math.random() - 0.5) * 2 * shakeAmt;
    ctx.save();
    ctx.translate(shakeX, shakeY);
    // re-draw scene at offset... or apply to canvas element transform
    ctx.restore();
  } else {
    // Animation complete — transition to GAME_OVER
    state.collisionAnim = null;
    state.gameState = 'GAME_OVER';
  }
}
```

### Initialisation Sequence

State is initialised in a strict order before the game loop starts. No system runs until all assets and config are ready.

```js
async function init() {
  // 1. Load config
  const cfg = await fetch('game-config.json').then(r => r.json());

  // 2. Set up canvas
  resizeCanvas(canvas, ctx);
  const bgCanvas = buildBackground(canvas.width, canvas.height);

  // 3. Load assets (non-blocking failures are silent)
  const ghostyImg = await loadImage('assets/ghosty.png');
  audioManager.load(cfg);

  // 4. Restore persistent state
  state.highScore = readHighScore();

  // 5. Initialise entity arrays
  initClouds(state, canvas.width, canvas.height, cfg);

  // 6. Wire input
  initInput();

  // 7. Start loop
  state.lastTimestamp = 0;
  requestAnimationFrame(gameLoop);
}
```

### Resetting State on Restart

`startGame` / `restartGame` must reset every field that gameplay modifies. Use `array.length = 0` to clear arrays in place (no allocation), and mutate `ghosty` fields directly.

```js
// Clear arrays in place — no new array allocation
state.pipes.length = 0;
state.particles.length = 0;
state.scorePopups.length = 0;

// Mutate ghosty in place
state.ghosty.x = canvas.width * 0.3;
state.ghosty.y = canvas.height / 2;
state.ghosty.vy = 0;
state.ghosty.prevY = state.ghosty.y;
```
