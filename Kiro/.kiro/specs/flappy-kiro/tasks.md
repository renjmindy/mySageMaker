# Implementation Plan: Flappy Kiro

## Overview

Implement Flappy Kiro as a vanilla JS browser game using HTML5 Canvas. The implementation follows the modular architecture defined in the design: `config.js` for constants, `game.js` for all game logic and systems, and `index.html` as the entry point. A `tests/` directory holds Vitest property-based and unit tests using fast-check.

## Tasks

- [ ] 1. Create project scaffold and config module
  - Create `index.html` with a single `<canvas>` element and script imports
  - `game-config.json` already exists at the project root with all physics and game parameters — load it via `fetch('game-config.json')` at startup before the game loop begins
  - Create `game.js` that fetches and stores the config, then initialises all systems
  - Create `package.json` with Vitest and fast-check as dev dependencies
  - Create `vitest.config.js` (or equivalent) to configure the test runner
  - _Requirements: 3.2, 3.5, 3.6, 3.9, 4.2, 4.7, 8.5, 10.5_

- [ ] 2. Implement localStorage high score module
  - Create `readHighScore()` and `writeHighScore(score)` functions in `game.js`
  - `readHighScore` reads `HS_STORAGE_KEY`, parses as integer, returns 0 for missing/corrupt values and overwrites corrupt entries with `'0'`
  - Wrap all `localStorage` access in try/catch for private-browsing safety
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 2.1 Write property test for high score persistence (P18)
    - **Property 18: High score is persisted to localStorage when beaten**
    - **Validates: Requirements 8.1**

  - [ ]* 2.2 Write property test for corrupt/missing localStorage (P19)
    - **Property 19: Corrupt or missing localStorage value defaults to 0**
    - **Validates: Requirements 8.3, 8.4**

- [ ] 3. Implement game state object and state machine transitions
  - Define the `state` object with all fields: `gameState`, `score`, `highScore`, `ghosty`, `pipes`, `particles`, `scorePopups`, `clouds`, `invincibleUntil`, `collisionAnim`, `pipeSpeed`, `lastTimestamp`, `newBest`
  - Implement `startGame()`: sets `gameState` to PLAYING, resets score to 0, sets `pipeSpeed` to `BASE_PIPE_SPEED`, activates invincibility window, clears pipes, positions Ghosty at canvas centre
  - Implement `restartGame()`: same as `startGame()` but called from GAME_OVER state
  - Implement `pauseGame()` / `resumeGame()`: toggle between PLAYING and PAUSED
  - Initialise `highScore` from `readHighScore()` on load
  - _Requirements: 1.1, 1.5, 2.2, 4.7, 4.8, 5.4, 6.1, 6.5, 7.5, 7.6, 7.7_

  - [ ]* 3.1 Write unit tests for state transitions
    - Test MENU → PLAYING on `startGame()`
    - Test `startGame()` resets score to 0 and retains highScore
    - Test `restartGame()` resets Ghosty position to canvas centre and clears pipes
    - Test PLAYING → PAUSED → PLAYING round-trip preserves pipe positions and Ghosty state
    - _Requirements: 1.1, 5.4, 6.1, 6.5, 7.5, 7.6, 7.7_

- [ ] 4. Implement physics system
  - Implement `updatePhysics(ghosty, canvasHeight)`: stores `prevY`, applies gravity, clamps to `TERMINAL_VELOCITY`, updates `y`, clamps ceiling at 0
  - Implement `flap(state)`: sets `ghosty.vy = FLAP_VELOCITY` only when `gameState === PLAYING`
  - Implement `getInterpolatedY(ghosty, alpha)`: returns `prevY + (y - prevY) * alpha`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7_

  - [ ]* 4.1 Write property test for physics step (P1)
    - **Property 1: Physics step integrates gravity and position correctly**
    - **Validates: Requirements 2.1, 2.3, 2.7**

  - [ ]* 4.2 Write property test for flap velocity (P2)
    - **Property 2: Flap always sets velocity to Flap_Velocity**
    - **Validates: Requirements 2.2**

  - [ ]* 4.3 Write property test for terminal velocity (P3)
    - **Property 3: Terminal velocity is never exceeded**
    - **Validates: Requirements 2.4**

  - [ ]* 4.4 Write property test for interpolation (P4)
    - **Property 4: Interpolated render position is a blend of previous and current**
    - **Validates: Requirements 2.5**

  - [ ]* 4.5 Write property test for flap ignored when paused (P17)
    - **Property 17: Flap input is ignored while paused**
    - **Validates: Requirements 6.6**

- [ ] 5. Implement pipe manager and object pool
  - Implement the `Pool` class with `acquire()` and `release(obj)` methods
  - Implement `PipePairPool` (max 6), `ParticlePool` (max 60), `ScorePopupPool` (max 8)
  - Implement `spawnPipe(state, canvasWidth, canvasHeight)`: acquires from pool, sets `x`, `gapCenterY` (random within Safe_Zone), `scored = false`
  - Implement `updatePipes(state, canvasWidth, canvasHeight)`: scrolls all pipes left by `pipeSpeed`, recycles pipes that exit left edge, spawns new pipe when rightmost pipe x < `canvasWidth - PIPE_SPACING`
  - Derive `topRect` and `bottomRect` from each `PipePair` on demand
  - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ]* 5.1 Write property test for pipe scrolling (P5)
    - **Property 5: Pipes scroll left by exactly Pipe_Speed each frame**
    - **Validates: Requirements 3.1**

  - [ ]* 5.2 Write property test for gap size (P6)
    - **Property 6: Generated pipe gap is exactly Gap_Size**
    - **Validates: Requirements 3.7**

  - [ ]* 5.3 Write property test for gap safe zone (P7)
    - **Property 7: Generated pipe gap centre is within Safe_Zone**
    - **Validates: Requirements 3.8**

- [ ] 6. Implement collision detection
  - Implement `getCircleHitbox(ghosty, spriteW, spriteH)`: returns `{ cx, cy, r }` using `HITBOX_INSET`
  - Implement `circleOverlapsRect(cx, cy, r, rect)`: circle-AABB nearest-point test
  - Implement `checkCollisions(state, now, canvasHeight)`: checks invincibility window, tests circle vs all pipe rects, ground, and ceiling; calls `triggerCollision(state)` on hit
  - `triggerCollision` plays `game_over.wav`, starts `collisionAnim`, updates high score if beaten, writes to localStorage
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9, 4.12, 4.13_

  - [ ]* 6.1 Write property test for circular hitbox derivation (P9)
    - **Property 9: Ghosty circular hitbox is correctly derived from sprite bounds**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 6.2 Write property test for collision detection (P10)
    - **Property 10: Collision is detected for all boundary and pipe overlaps**
    - **Validates: Requirements 4.3, 4.4, 4.5, 4.6**

  - [ ]* 6.3 Write property test for invincibility guard (P11)
    - **Property 11: Invincibility window prevents collision detection**
    - **Validates: Requirements 4.6, 4.8**

  - [ ]* 6.4 Write property test for high score update on collision (P12)
    - **Property 12: High score is updated when current score exceeds it**
    - **Validates: Requirements 4.13**

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement scorer and speed progression
  - Implement `checkScoring(state)`: iterates pipes, sets `pipe.scored = true` when `ghosty.x > pipe.x + PIPE_WIDTH / 2`, increments score, spawns score popup, plays score sound, applies speed increment at milestones
  - Speed increment: `state.pipeSpeed = min(pipeSpeed + SPEED_INCREMENT, MAX_PIPE_SPEED)` when `score % SPEED_MILESTONE === 0`
  - _Requirements: 3.9, 3.10, 3.11, 5.1, 5.2, 5.4_

  - [ ]* 8.1 Write property test for score increment (P13)
    - **Property 13: Scoring increments by exactly 1 per pipe passed**
    - **Validates: Requirements 5.1**

  - [ ]* 8.2 Write property test for speed milestone (P8)
    - **Property 8: Pipe speed increases at score milestones and is capped**
    - **Validates: Requirements 3.10, 3.11**

- [ ] 9. Implement particle system and score popups
  - Implement `emitParticle(state, now)`: acquires from `ParticlePool`, sets `x`, `y`, `born`, `duration`
  - Implement `updateParticles(state, now)`: releases particles where `(now - born) >= duration` back to pool
  - Implement `spawnScorePopup(state, now)`: acquires from `ScorePopupPool`, sets position and timestamps
  - Implement `updateScorePopups(state, now)`: releases expired popups back to pool
  - _Requirements: 9.7, 9.8, 9.9_

  - [ ]* 9.1 Write property test for particle lifecycle (P21)
    - **Property 21: Particle lifecycle — emission and expiry**
    - **Validates: Requirements 9.7, 9.8**

  - [ ]* 9.2 Write property test for score popup lifecycle (P22)
    - **Property 22: Score popup is created on score increment and expires after duration**
    - **Validates: Requirements 9.9**

- [ ] 10. Implement cloud scroller
  - Initialise two `CLOUD_LAYERS` arrays at game start with randomised x positions and opacities `< 1.0`
  - Implement `updateClouds(state, canvasWidth)`: always runs regardless of `gameState`; scrolls each layer at its own speed; wraps clouds to right edge when `x + cloud.width < 0`
  - Layer 0 (far): speed `0.3`; Layer 1 (near): speed `0.7`
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 10.1 Write property test for cloud layer speeds differ (P23)
    - **Property 23: Cloud layers scroll at distinct speeds**
    - **Validates: Requirements 11.2**

  - [ ]* 10.2 Write property test for cloud opacity (P24)
    - **Property 24: All clouds have opacity strictly less than 1.0**
    - **Validates: Requirements 11.3**

  - [ ]* 10.3 Write property test for cloud wrap (P25)
    - **Property 25: Clouds wrap from left edge to right edge**
    - **Validates: Requirements 11.4**

  - [ ]* 10.4 Write property test for clouds scroll while paused (P16)
    - **Property 16: Clouds continue scrolling while paused**
    - **Validates: Requirements 6.3, 11.6**

  - [ ]* 10.5 Write property test for physics halts when paused (P15)
    - **Property 15: Pipe movement and Ghosty physics halt while paused**
    - **Validates: Requirements 6.4**

- [ ] 11. Implement audio manager
  - Implement `loadSound(path)` returning an `HTMLAudioElement` with `onerror` silent-fail flag
  - Implement `playSound(audio)`: resets `currentTime` to 0 and calls `.play().catch(() => {})` wrapped in try/catch
  - Load `jump.wav`, `game_over.wav`, and a score sound at startup
  - Implement `AudioManager` with `playBgMusic()`, `pauseBgMusic()`, `stopBgMusic()` methods
  - Wire audio calls into `flap()`, `triggerCollision()`, `checkScoring()`, and state transitions
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11_

  - [ ]* 11.1 Write unit tests for audio manager silent fail
    - Test that `playSound` with a failed audio element does not throw
    - Test that missing background music does not prevent game from running
    - _Requirements: 10.2, 10.7_

- [ ] 12. Implement renderer
  - Pre-render sketchy background to an offscreen canvas at init; blit with `drawImage` each frame
  - Draw in z-order: background blit → cloud layers → pipes (green rect + darker cap) → particle trail → Ghosty sprite (rotated by `vy`) → score popups → score bar → state overlay → collision animation
  - Implement Ghosty sprite rotation: positive angle when `vy > 0`, zero/negative when `vy ≤ 0`
  - Implement score bar as a bottom strip showing current score and high score at all game states
  - Implement MENU overlay (title, "Best", idle float animation, start prompt)
  - Implement PAUSED overlay (semi-transparent, "PAUSED" text, resume prompt)
  - Implement GAME_OVER overlay (final score, high score, "New Best!" when applicable, restart prompt)
  - Implement collision animation: white flash phase then screen-shake phase, total ≤ 500ms; on completion set `gameState` to GAME_OVER
  - Fallback: render white rectangle if `ghosty.png` fails to load
  - _Requirements: 1.2, 1.4, 4.9, 4.10, 4.11, 5.2, 5.3, 6.2, 7.1, 7.2, 7.3, 7.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [ ]* 12.1 Write property test for sprite rotation direction (P20)
    - **Property 20: Ghosty sprite rotation reflects velocity direction**
    - **Validates: Requirements 9.5**

  - [ ]* 12.2 Write property test for score bar across all states (P14)
    - **Property 14: Score bar displays high score across all game states**
    - **Validates: Requirements 5.3**

- [ ] 13. Implement input handler and game loop
  - Implement `onKeyDown` / `onPointerDown` event listeners wired to `handleAction()` and `handlePause()`
  - `handleAction()`: MENU → `startGame()`, PLAYING → `flap()`, GAME_OVER → `restartGame()`, PAUSED → no-op
  - `handlePause()`: PLAYING → `pauseGame()`, PAUSED → `resumeGame()`
  - Implement the `requestAnimationFrame` game loop: compute `dt`, call `updateClouds`, then if PLAYING call `updatePhysics`, `updatePipes`, `checkCollisions`, `checkScoring`, `emitParticle`, `updateParticles`, `updateScorePopups`; always call renderer
  - Handle canvas resize: update canvas dimensions and rescale all positional values proportionally
  - _Requirements: 1.3, 1.5, 2.6, 6.1, 6.3, 6.4, 6.5, 6.6, 12.1, 12.2, 12.3_

  - [ ]* 13.1 Write unit tests for input handler routing
    - Test that Space/tap in MENU calls `startGame()`
    - Test that Space/tap in PAUSED does not call `flap()`
    - Test that Escape/P toggles PLAYING ↔ PAUSED
    - _Requirements: 1.5, 6.1, 6.5, 6.6_

- [ ] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests reference design document property numbers (P1–P25)
- Checkpoints ensure incremental validation before moving to the next phase
- The `Pool` class must be implemented before particle, popup, and pipe tasks that depend on it
