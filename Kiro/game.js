// Flappy Kiro — game.js
// Single file for all game logic: state, systems, renderer, input, loop.
// Config is loaded from game-config.json at startup via fetch.

// ─── Config ──────────────────────────────────────────────────────────────────
/** @type {Object} cfg — populated by loadConfig() before the game loop starts */
export let cfg = null;

export async function loadConfig() {
  cfg = await fetch('game-config.json').then(r => r.json());
}

// ─── Constants (derived from cfg after load) ─────────────────────────────────
// These are set by initConstants() once cfg is available.
export let GRAVITY            = 0;
export let FLAP_VELOCITY      = 0;
export let TERMINAL_VELOCITY  = 0;
export let BASE_PIPE_SPEED    = 0;
export let GAP_SIZE           = 0;
export let PIPE_SPACING       = 0;
export let GAP_MARGIN         = 0;
export let SPEED_INCREMENT    = 0;
export let SPEED_MILESTONE    = 0;
export let MAX_PIPE_SPEED     = 0;
export let HITBOX_INSET       = 0;
export let INVINCIBILITY_MS   = 0;
export let PARTICLE_DURATION  = 0;
export let SCORE_POPUP_DURATION = 0;
export let COLLISION_ANIM_MS  = 0;
export let BG_MUSIC_PATH      = '';
export let HS_STORAGE_KEY     = '';

export function initConstants() {
  GRAVITY           = cfg.physics.gravity;
  FLAP_VELOCITY     = cfg.physics.jumpVelocity;
  TERMINAL_VELOCITY = cfg.physics.terminalVelocity;
  BASE_PIPE_SPEED   = cfg.pipes.wallSpeed;
  GAP_SIZE          = cfg.pipes.gapSize;
  PIPE_SPACING      = cfg.pipes.wallSpacing;
  GAP_MARGIN        = cfg.pipes.gapMargin;
  SPEED_INCREMENT   = cfg.pipes.speedIncrement;
  SPEED_MILESTONE   = cfg.pipes.speedMilestone;
  MAX_PIPE_SPEED    = cfg.pipes.maxWallSpeed;
  HITBOX_INSET      = cfg.collision.hitboxInset;
  INVINCIBILITY_MS  = cfg.collision.invincibilityMs;
  PARTICLE_DURATION = cfg.visual.particleDuration;
  SCORE_POPUP_DURATION = cfg.visual.scorePopupDuration;
  COLLISION_ANIM_MS = cfg.visual.collisionAnimMs;
  BG_MUSIC_PATH     = cfg.audio.bgMusicPath;
  HS_STORAGE_KEY    = cfg.storage.highScoreKey;
}

// ─── Sprite / layout constants ────────────────────────────────────────────────
export const SPRITE_W      = 48;
export const SPRITE_H      = 48;
export const PIPE_WIDTH    = 60;
export const SCORE_BAR_H   = 48;

// ─── Cloud layer config ───────────────────────────────────────────────────────
export const CLOUD_LAYER_SPEEDS = [0.3, 0.7]; // far → near

// ─── Game State Object ────────────────────────────────────────────────────────
export const state = {
  gameState: 'MENU',       // 'MENU' | 'PLAYING' | 'PAUSED' | 'GAME_OVER'
  score: 0,
  highScore: 0,
  ghosty: { x: 0, y: 0, vy: 0, prevY: 0 },
  pipes: [],               // active PipePair objects
  particles: [],           // active Particle objects
  scorePopups: [],         // active ScorePopup objects
  clouds: [[], []],        // two Cloud_Layer arrays
  invincibleUntil: 0,      // timestamp ms
  collisionAnim: null,     // { startTime, phase } | null
  pipeSpeed: 0,
  lastTimestamp: 0,
  newBest: false,
};

// ─── localStorage ─────────────────────────────────────────────────────────────
export function readHighScore() {
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

export function writeHighScore(score) {
  try { localStorage.setItem(HS_STORAGE_KEY, String(score)); } catch (_) {}
}

// ─── Physics ──────────────────────────────────────────────────────────────────
/**
 * Update Ghosty's physics for one frame.
 * @param {Object} ghosty - { x, y, vy, prevY }
 * @param {number} canvasHeight
 * @param {number} dt - seconds elapsed since last frame
 */
export function updatePhysics(ghosty, canvasHeight, dt) {
  ghosty.prevY = ghosty.y;
  ghosty.vy = Math.min(ghosty.vy + GRAVITY * dt, TERMINAL_VELOCITY);
  ghosty.y += ghosty.vy * dt;
  // Ceiling clamp
  if (ghosty.y < 0) { ghosty.y = 0; ghosty.vy = Math.max(ghosty.vy, 0); }
}

/** Apply flap impulse — only when PLAYING. */
export function flap(st) {
  if (st.gameState !== 'PLAYING') return;
  st.ghosty.vy = FLAP_VELOCITY;
}

/** Interpolated render y between previous and current physics position. */
export function getInterpolatedY(ghosty, alpha) {
  return ghosty.prevY + (ghosty.y - ghosty.prevY) * alpha;
}

// ─── Pipe Manager ─────────────────────────────────────────────────────────────
/** Derive top and bottom pipe rectangles from a PipePair. */
export function getPipeRects(pipe, canvasHeight) {
  const topH = pipe.gapCenterY - GAP_SIZE / 2;
  const botY = pipe.gapCenterY + GAP_SIZE / 2;
  return {
    topRect:    { x: pipe.x, y: 0,    w: PIPE_WIDTH, h: topH },
    bottomRect: { x: pipe.x, y: botY, w: PIPE_WIDTH, h: canvasHeight - botY },
  };
}

export function spawnPipe(st, canvasWidth, canvasHeight) {
  const minCY = GAP_MARGIN + GAP_SIZE / 2;
  const maxCY = canvasHeight - SCORE_BAR_H - GAP_MARGIN - GAP_SIZE / 2;
  const gapCenterY = minCY + Math.random() * (maxCY - minCY);
  st.pipes.push({ x: canvasWidth, gapCenterY, scored: false });
}

export function updatePipes(st, canvasWidth, canvasHeight, dt) {
  for (let i = st.pipes.length - 1; i >= 0; i--) {
    st.pipes[i].x -= st.pipeSpeed * dt;
    if (st.pipes[i].x + PIPE_WIDTH < 0) {
      st.pipes.splice(i, 1);
    }
  }
  const rightmost = st.pipes.reduce((max, p) => Math.max(max, p.x), -Infinity);
  if (st.pipes.length === 0 || rightmost < canvasWidth - PIPE_SPACING) {
    spawnPipe(st, canvasWidth, canvasHeight);
  }
}

// ─── Collision Detection ──────────────────────────────────────────────────────
export function getCircleHitbox(ghosty) {
  const cx = ghosty.x + SPRITE_W / 2;
  const cy = ghosty.y + SPRITE_H / 2;
  const r  = Math.min(SPRITE_W, SPRITE_H) / 2 - HITBOX_INSET;
  return { cx, cy, r };
}

export function circleOverlapsRect(cx, cy, r, rect) {
  const nearestX = Math.max(rect.x, Math.min(cx, rect.x + rect.w));
  const nearestY = Math.max(rect.y, Math.min(cy, rect.y + rect.h));
  const dx = cx - nearestX;
  const dy = cy - nearestY;
  return (dx * dx + dy * dy) <= r * r;
}

export function checkCollisions(st, now, canvasHeight) {
  if (now < st.invincibleUntil) return;
  const { cx, cy, r } = getCircleHitbox(st.ghosty);
  for (const pipe of st.pipes) {
    const { topRect, bottomRect } = getPipeRects(pipe, canvasHeight);
    if (circleOverlapsRect(cx, cy, r, topRect))    { triggerCollision(st, now); return; }
    if (circleOverlapsRect(cx, cy, r, bottomRect)) { triggerCollision(st, now); return; }
  }
  if (cy + r >= canvasHeight - SCORE_BAR_H) { triggerCollision(st, now); return; }
  if (cy - r <= 0)                           { triggerCollision(st, now); }
}

export function triggerCollision(st, now) {
  if (st.score > st.highScore) {
    st.highScore = st.score;
    st.newBest = true;
    writeHighScore(st.highScore);
  }
  st.collisionAnim = { startTime: now, phase: 'flash' };
  // Audio wired in later task
}

// ─── Scorer ───────────────────────────────────────────────────────────────────
export function checkScoring(st) {
  for (const pipe of st.pipes) {
    if (!pipe.scored && st.ghosty.x > pipe.x + PIPE_WIDTH / 2) {
      pipe.scored = true;
      st.score++;
      if (st.score % SPEED_MILESTONE === 0) {
        st.pipeSpeed = Math.min(st.pipeSpeed + SPEED_INCREMENT, MAX_PIPE_SPEED);
      }
      // spawnScorePopup / playScoreSound wired in later tasks
    }
  }
}

// ─── Particle System ──────────────────────────────────────────────────────────
export function emitParticle(st, now) {
  st.particles.push({ x: st.ghosty.x, y: st.ghosty.y, born: now, duration: PARTICLE_DURATION });
}

export function updateParticles(st, now) {
  for (let i = st.particles.length - 1; i >= 0; i--) {
    if (now - st.particles[i].born >= st.particles[i].duration) {
      st.particles.splice(i, 1);
    }
  }
}

// ─── Score Popups ─────────────────────────────────────────────────────────────
export function spawnScorePopup(st, now, canvasWidth) {
  st.scorePopups.push({ x: canvasWidth / 2, y: 60, born: now, duration: SCORE_POPUP_DURATION });
}

export function updateScorePopups(st, now) {
  for (let i = st.scorePopups.length - 1; i >= 0; i--) {
    if (now - st.scorePopups[i].born >= st.scorePopups[i].duration) {
      st.scorePopups.splice(i, 1);
    }
  }
}

// ─── Cloud Scroller ───────────────────────────────────────────────────────────
export function initClouds(st, canvasWidth, canvasHeight) {
  st.clouds = CLOUD_LAYER_SPEEDS.map(() => {
    return Array.from({ length: 5 }, (_, i) => ({
      x:       Math.random() * canvasWidth,
      y:       Math.random() * (canvasHeight * 0.6),
      width:   60 + Math.random() * 80,
      height:  20 + Math.random() * 30,
      opacity: 0.2 + Math.random() * 0.5, // strictly < 1.0
    }));
  });
}

export function updateClouds(st, canvasWidth, dt) {
  // Always runs regardless of gameState (continues during PAUSED)
  for (let li = 0; li < st.clouds.length; li++) {
    const speed = CLOUD_LAYER_SPEEDS[li];
    for (const cloud of st.clouds[li]) {
      cloud.x -= speed * dt * 60; // speed is in px/frame at 60fps; convert to px/s
      if (cloud.x + cloud.width < 0) {
        cloud.x = canvasWidth + Math.random() * 100;
      }
    }
  }
}

// ─── Audio Manager ────────────────────────────────────────────────────────────
export function loadSound(path) {
  const audio = new Audio();
  audio._failed = false;
  audio.onerror = () => { audio._failed = true; };
  audio.src = path;
  return audio;
}

export function playSound(audio) {
  if (!audio || audio._failed) return;
  try {
    audio.currentTime = 0;
    audio.play().catch(() => {});
  } catch (_) {}
}

export class AudioManager {
  constructor() {
    this._jump     = null;
    this._gameOver = null;
    this._bgMusic  = null;
  }
  load() {
    this._jump     = loadSound('assets/jump.wav');
    this._gameOver = loadSound('assets/game_over.wav');
    if (BG_MUSIC_PATH) {
      this._bgMusic = loadSound(BG_MUSIC_PATH);
      if (this._bgMusic) this._bgMusic.loop = true;
    }
  }
  playJump()    { playSound(this._jump); }
  playGameOver(){ playSound(this._gameOver); }
  playBgMusic() {
    if (!this._bgMusic || this._bgMusic._failed) return;
    try { this._bgMusic.play().catch(() => {}); } catch (_) {}
  }
  pauseBgMusic() {
    if (!this._bgMusic || this._bgMusic._failed) return;
    try { this._bgMusic.pause(); } catch (_) {}
  }
  stopBgMusic() {
    if (!this._bgMusic || this._bgMusic._failed) return;
    try { this._bgMusic.pause(); this._bgMusic.currentTime = 0; } catch (_) {}
  }
}

// ─── State Machine ────────────────────────────────────────────────────────────
let _canvas = null;
let _audioManager = null;

export function startGame() {
  const w = _canvas ? _canvas.width  : 480;
  const h = _canvas ? _canvas.height : 640;
  state.gameState      = 'PLAYING';
  state.score          = 0;
  state.newBest        = false;
  state.pipeSpeed      = BASE_PIPE_SPEED;
  state.invincibleUntil = performance.now() + INVINCIBILITY_MS;
  state.pipes          = [];
  state.particles      = [];
  state.scorePopups    = [];
  state.collisionAnim  = null;
  state.ghosty.x       = w / 4;
  state.ghosty.y       = h / 2 - SPRITE_H / 2;
  state.ghosty.prevY   = state.ghosty.y;
  state.ghosty.vy      = 0;
  spawnPipe(state, w, h);
  if (_audioManager) _audioManager.playBgMusic();
}

export function restartGame() {
  startGame();
}

export function pauseGame() {
  if (state.gameState !== 'PLAYING') return;
  state.gameState = 'PAUSED';
  if (_audioManager) _audioManager.pauseBgMusic();
}

export function resumeGame() {
  if (state.gameState !== 'PAUSED') return;
  state.gameState = 'PLAYING';
  state.lastTimestamp = performance.now(); // reset dt to avoid jump
  if (_audioManager) _audioManager.playBgMusic();
}

// ─── Input Handler ────────────────────────────────────────────────────────────
function handleAction() {
  if (state.gameState === 'MENU')      { startGame(); return; }
  if (state.gameState === 'PLAYING')   { flap(state); return; }
  if (state.gameState === 'GAME_OVER') { restartGame(); }
  // PAUSED → no-op
}

function handlePause() {
  if (state.gameState === 'PLAYING') { pauseGame();  return; }
  if (state.gameState === 'PAUSED')  { resumeGame(); }
}

function onKeyDown(e) {
  if (e.code === 'Space')                        { e.preventDefault(); handleAction(); }
  if (e.code === 'Escape' || e.code === 'KeyP')  { handlePause(); }
}

function onPointerDown() { handleAction(); }

// ─── Renderer (stub — full implementation in later task) ─────────────────────
function render(canvas, ctx, now) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#87CEEB';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // Full renderer wired in Task 12
}

// ─── Game Loop ────────────────────────────────────────────────────────────────
function loop(timestamp) {
  const dt = Math.min((timestamp - (state.lastTimestamp || timestamp)) / 1000, 0.05);
  state.lastTimestamp = timestamp;

  const canvas = _canvas;
  const ctx    = canvas.getContext('2d');
  const w      = canvas.width;
  const h      = canvas.height;

  updateClouds(state, w, dt);

  if (state.gameState === 'PLAYING') {
    updatePhysics(state.ghosty, h, dt);
    updatePipes(state, w, h, dt);
    checkCollisions(state, timestamp, h);
    checkScoring(state);
    emitParticle(state, timestamp);
    updateParticles(state, timestamp);
    updateScorePopups(state, timestamp);

    // Collision animation completion → GAME_OVER
    if (state.collisionAnim) {
      const elapsed = timestamp - state.collisionAnim.startTime;
      if (elapsed >= COLLISION_ANIM_MS) {
        state.gameState = 'GAME_OVER';
        state.collisionAnim = null;
        if (_audioManager) _audioManager.stopBgMusic();
      }
    }
  }

  render(canvas, ctx, timestamp);
  requestAnimationFrame(loop);
}

// ─── Entry Point ──────────────────────────────────────────────────────────────
async function main() {
  await loadConfig();
  initConstants();

  _canvas = document.getElementById('gameCanvas');
  _canvas.width  = window.innerWidth;
  _canvas.height = window.innerHeight;

  state.highScore = readHighScore();
  initClouds(state, _canvas.width, _canvas.height);

  _audioManager = new AudioManager();
  _audioManager.load();

  window.addEventListener('keydown', onKeyDown);
  _canvas.addEventListener('pointerdown', onPointerDown);

  window.addEventListener('resize', () => {
    _canvas.width  = window.innerWidth;
    _canvas.height = window.innerHeight;
  });

  requestAnimationFrame(loop);
}

// Only run main() in the browser (not during tests)
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  main();
}
