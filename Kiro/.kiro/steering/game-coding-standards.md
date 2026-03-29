# JavaScript Game Coding Standards

## Class Naming Conventions

- Classes use `PascalCase`: `Pool`, `AudioManager`, `PipePair`, `CollisionAnimState`
- Instances use `camelCase`: `pipePairPool`, `audioManager`
- Constants use `SCREAMING_SNAKE_CASE`: `GRAVITY`, `FLAP_VELOCITY`, `TERMINAL_VELOCITY`, `MAX_PIPE_SPEED`
- Game state strings are uppercase literals: `'MENU'`, `'PLAYING'`, `'PAUSED'`, `'GAME_OVER'`
- Private/internal fields are prefixed with `_`: `_pool`, `_active`, `_failed`
- Boolean flags use `is`/`has`/`can` prefixes: `isLoaded`, `hasScored`, `canFlap`

## File Structure

```
index.html        # Entry point — canvas + script imports only
game-config.json  # All tunable constants (never hardcode magic numbers in game.js)
game.js           # All game logic: state, systems, renderer, input, loop
tests/            # Vitest + fast-check tests
  physics.test.js
  pipes.test.js
  collision.test.js
  scoring.test.js
  storage.test.js
  audio.test.js
  renderer.test.js
  input.test.js
  clouds.test.js
  particles.test.js
```

## JavaScript Patterns

### Config Loading
Always load `game-config.json` via `fetch` before starting the game loop. Never hardcode physics values.

```js
const cfg = await fetch('game-config.json').then(r => r.json());
```

### Object Pooling
Use the `Pool` class for all short-lived objects (particles, score popups, pipe pairs). Never `new` inside the game loop.

```js
class Pool {
  constructor(maxSize, factory) {
    this._pool = Array.from({ length: maxSize }, factory);
  }
  acquire() { return this._pool.length ? this._pool.pop() : null; }
  release(obj) { this._pool.push(obj); }
}
```

- `ParticlePool`: max 60
- `ScorePopupPool`: max 8
- `PipePairPool`: max 6

### State Machine
Game state is a single string field on the `state` object. All transitions go through named functions — never mutate `gameState` directly outside of `startGame`, `restartGame`, `pauseGame`, `resumeGame`, `triggerCollision`.

```js
// Good
startGame();

// Bad
state.gameState = 'PLAYING';
```

### Pure-ish Systems
System functions take `state` (and optionally `dt`, `now`, canvas dimensions) as arguments. They must not read from the DOM or global scope except for constants.

```js
// Good
function updatePhysics(state, dt) { ... }

// Bad
function updatePhysics() { /* reads global state */ }
```

### Time-Based Physics
All physics values are in `px/s` or `px/s²`. Multiply by `dt` (seconds) each frame. Cap `dt` at `0.05` to prevent spiral-of-death on tab blur.

```js
const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05);
ghosty.vy = Math.min(ghosty.vy + cfg.physics.gravity * dt, cfg.physics.terminalVelocity);
ghosty.y += ghosty.vy * dt;
```

### Silent Fail Pattern
All audio and localStorage access must be wrapped in try/catch. Never surface errors to the player.

```js
function playSound(audio) {
  if (!audio || audio._failed) return;
  try {
    audio.currentTime = 0;
    audio.play().catch(() => {});
  } catch (_) {}
}

function readHighScore() {
  try {
    const raw = localStorage.getItem(HS_STORAGE_KEY);
    const n = parseInt(raw, 10);
    if (!Number.isInteger(n) || n < 0) {
      localStorage.setItem(HS_STORAGE_KEY, '0');
      return 0;
    }
    return n;
  } catch (_) { return 0; }
}
```

## Performance Optimization Guidelines

### No Allocations in the Hot Path
The game loop, physics, collision, and rendering functions must not allocate objects. Use pools, mutate in place, and avoid `filter()`, `map()`, or spread operators inside `requestAnimationFrame`.

```js
// Bad — allocates new array every frame
state.particles = state.particles.filter(p => now - p.born < p.duration);

// Good — release back to pool, iterate in place
for (let i = state.particles.length - 1; i >= 0; i--) {
  if (now - state.particles[i].born >= state.particles[i].duration) {
    particlePool.release(state.particles[i]);
    state.particles.splice(i, 1);
  }
}
```

### Offscreen Canvas for Static Backgrounds
Pre-render the sketchy background once at init to an offscreen canvas. Blit it each frame with a single `drawImage` call.

```js
// Init (once)
const bgCanvas = document.createElement('canvas');
drawSketchyBackground(bgCanvas.getContext('2d'), width, height);

// Each frame
ctx.drawImage(bgCanvas, 0, 0);
```

### Batch Canvas State Changes
Minimise `save`/`restore`, `globalAlpha`, and transform changes. Group draws by shared style.

```js
// Good — set alpha once per layer
ctx.globalAlpha = layer.opacity;
for (const cloud of layer.clouds) drawCloud(ctx, cloud);
ctx.globalAlpha = 1;
```

### Dirty Flags for Text
Only re-render score text when the value changes. Use a dirty flag.

```js
if (state.score !== lastRenderedScore) {
  renderScoreBar(ctx, state);
  lastRenderedScore = state.score;
}
```

### Cap dt
Always cap the frame delta to prevent physics explosions after tab blur or slow frames.

```js
const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05);
```

### Fixed-Size Cloud Arrays
Cloud arrays are initialised once at startup and never resized. Clouds are repositioned (wrapped), never added or removed.

## Testing Standards

### Property Tests
Every property test must:
- Include a comment tag: `// Feature: flappy-kiro, Property N: <description>`
- Use `fc.assert(fc.property(...))` — one assertion per property
- Run at minimum 100 iterations (`numRuns: 200` for critical properties)

```js
test('P1: physics step integrates gravity correctly', () => {
  // Feature: flappy-kiro, Property 1: Physics step integrates gravity and position correctly
  fc.assert(
    fc.property(
      fc.record({ vy: fc.float({ min: -500, max: 500 }), y: fc.float({ min: 0, max: 600 }) }),
      ({ vy, y }) => { ... }
    ),
    { numRuns: 200 }
  );
});
```

### Unit Tests
Focus on state transitions, edge cases, and error conditions. Use descriptive test names that reference the requirement.

```js
test('startGame() resets score to 0 and retains highScore', () => { ... });
test('readHighScore() returns 0 for corrupt localStorage value', () => { ... });
```

### Test File Naming
Mirror the system under test: `physics.test.js`, `collision.test.js`, `storage.test.js`, etc.

---

## Entity-Component Patterns

### Prefer Data-Oriented Design Over Deep Inheritance

Avoid class hierarchies for game entities. Instead, compose behaviour from plain data objects and standalone system functions.

```js
// Bad — inheritance hierarchy
class Entity { update() {} }
class MovingEntity extends Entity { update() { this.x += this.vx; } }
class Enemy extends MovingEntity { update() { super.update(); this.attack(); } }

// Good — flat data + systems
const enemy = { x: 0, y: 0, vx: 1, vy: 0, health: 3, type: 'enemy' };
function moveSystem(entities, dt) {
  for (const e of entities) { e.x += e.vx * dt; e.y += e.vy * dt; }
}
function attackSystem(enemies, player) { ... }
```

### Component Flags Over Subclasses

Use boolean flags or type strings on entity objects to vary behaviour, rather than creating a new subclass per variant.

```js
// Good
const entity = {
  x, y, vx, vy,
  isCollidable: true,
  isRenderable: true,
  isScorable: false,
  type: 'pipe',        // 'pipe' | 'particle' | 'cloud' | 'ghosty'
};
```

### Systems Are Pure Functions

Each system receives only what it needs. No system reads from global state or the DOM directly.

```js
// System signature pattern
function updateSystem(relevantEntities, dt, cfg) { ... }
function renderSystem(ctx, relevantEntities, state) { ... }
```

### System Execution Order

Systems must run in a defined, deterministic order each frame. Document the order explicitly.

```
1. Input collection      (translate events → intent flags)
2. Physics update        (apply forces, integrate positions)
3. Pipe / entity update  (scroll, spawn, recycle)
4. Collision detection   (read positions, write collision events)
5. Scoring               (consume collision/pass events, update score)
6. Particle update       (age and expire particles)
7. Cloud update          (always runs, even when paused)
8. Renderer              (read all state, draw to canvas)
```

---

## Game Loop Structure

### Canonical Loop Pattern

```js
function gameLoop(timestamp) {
  const dt = Math.min((timestamp - state.lastTimestamp) / 1000, 0.05);
  state.lastTimestamp = timestamp;

  // Always update
  updateClouds(state, canvas.width, dt);

  // Only update gameplay systems when PLAYING
  if (state.gameState === 'PLAYING') {
    updatePhysics(state, dt);
    updatePipes(state, canvas.width, canvas.height, dt);
    checkCollisions(state, timestamp, canvas.height);
    checkScoring(state);
    emitParticle(state, timestamp);
    updateParticles(state, timestamp);
    updateScorePopups(state, timestamp);
  }

  // Always render
  render(ctx, state, canvas, timestamp);

  requestAnimationFrame(gameLoop);
}
```

### Loop Invariants

- `dt` is always capped at `0.05s` — never trust raw frame deltas
- `lastTimestamp` is updated at the top of every frame, before any system runs
- The renderer always runs regardless of game state — it handles its own state-based branching
- Cloud updates always run regardless of game state (parallax continues during pause)
- Never call `cancelAnimationFrame` to pause — use the `gameState` guard instead

### Initialisation Sequence

```
1. fetch('game-config.json')         → store as cfg
2. Load image assets (ghosty.png)    → store refs, set _failed on error
3. Load audio assets                 → AudioManager.load(...)
4. Read highScore from localStorage  → state.highScore
5. Initialise cloud layers           → fixed arrays, random positions
6. Pre-render offscreen background   → bgCanvas
7. Attach input listeners            → keydown, pointerdown
8. Attach resize listener            → update canvas + rescale
9. Set gameState = 'MENU'
10. requestAnimationFrame(gameLoop)  → start loop
```

### Pause Without Cancelling RAF

Never cancel the animation frame to implement pause. Keep the loop running and gate systems behind the state check. This keeps cloud animation and the renderer active.

```js
// Bad
if (paused) cancelAnimationFrame(rafId);

// Good
if (state.gameState === 'PLAYING') {
  updatePhysics(state, dt);
  // ...
}
// renderer always called below
render(ctx, state, canvas, timestamp);
```

---

## Memory Management

### Pre-Allocate Everything at Init

All arrays and object pools must be sized and filled at startup. Nothing is allocated during gameplay.

```js
// Good — allocate at init
const particlePool = new Pool(60, () => ({ x: 0, y: 0, born: 0, duration: 0 }));
const clouds = [
  Array.from({ length: 6 }, () => ({ x: 0, y: 0, width: 0, height: 0, opacity: 0 })),
  Array.from({ length: 5 }, () => ({ x: 0, y: 0, width: 0, height: 0, opacity: 0 })),
];
```

### Mutate, Don't Replace

Reuse objects by resetting their fields. Never replace an object with a new one during the game loop.

```js
// Bad — creates new object
state.ghosty = { x: canvas.width / 2, y: canvas.height / 2, vy: 0, prevY: 0 };

// Good — mutate in place
state.ghosty.x = canvas.width / 2;
state.ghosty.y = canvas.height / 2;
state.ghosty.vy = 0;
state.ghosty.prevY = state.ghosty.y;
```

### Avoid Closures in Hot Paths

Closures capture scope and can prevent GC of outer variables. Prefer named functions over inline arrow functions inside `requestAnimationFrame`.

```js
// Bad — new closure every frame
requestAnimationFrame((ts) => { update(ts); render(ts); requestAnimationFrame(...) });

// Good — named function, no new closure
function gameLoop(ts) {
  update(ts);
  render(ts);
  requestAnimationFrame(gameLoop);
}
```

### String Interning for State Comparisons

Game state comparisons happen every frame. Use `===` with string literals — JS engines intern short repeated strings, making these comparisons O(1) pointer checks.

```js
if (state.gameState === 'PLAYING') { ... }   // fast — interned string comparison
```

### Typed Arrays for High-Frequency Numeric Data

For particle positions or other large numeric datasets, prefer `Float32Array` over plain arrays to reduce GC pressure and improve cache locality.

```js
// For larger particle counts (50+), typed arrays improve cache performance
const particleX = new Float32Array(MAX_PARTICLES);
const particleY = new Float32Array(MAX_PARTICLES);
```

### Event Listener Hygiene

Add event listeners once at init. Never add listeners inside the game loop or inside component constructors that run repeatedly.

```js
// Add once at startup
window.addEventListener('keydown', onKeyDown);
canvas.addEventListener('pointerdown', onPointerDown);
window.addEventListener('resize', onResize);
```

### Canvas Context State Hygiene

Always restore canvas context state after transforms or alpha changes. Leaked state causes subtle rendering bugs that are hard to trace.

```js
// Good — always paired
ctx.save();
ctx.translate(shakeX, shakeY);
renderScene(ctx, state);
ctx.restore();

// Also acceptable for simple alpha changes
const prevAlpha = ctx.globalAlpha;
ctx.globalAlpha = 0.5;
drawOverlay(ctx);
ctx.globalAlpha = prevAlpha;
```
