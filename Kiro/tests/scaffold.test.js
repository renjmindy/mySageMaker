// Smoke tests for Task 1: project scaffold and config module
import { describe, it, expect, beforeAll, vi } from 'vitest';

// Mock fetch so we can test loadConfig without a real server
const mockCfg = {
  physics:   { gravity: 800, jumpVelocity: -300, terminalVelocity: 600 },
  pipes:     { wallSpeed: 120, gapSize: 140, wallSpacing: 350, gapMargin: 60, speedIncrement: 20, speedMilestone: 5, maxWallSpeed: 300 },
  collision: { hitboxInset: 8, invincibilityMs: 1500 },
  visual:    { particleDuration: 500, scorePopupDuration: 700, collisionAnimMs: 500 },
  audio:     { bgMusicPath: 'assets/background.mp3' },
  storage:   { highScoreKey: 'flappyKiroHighScore' },
};

vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(mockCfg) })));

import {
  loadConfig, initConstants, cfg,
  GRAVITY, FLAP_VELOCITY, TERMINAL_VELOCITY,
  BASE_PIPE_SPEED, GAP_SIZE, PIPE_SPACING, GAP_MARGIN,
  SPEED_INCREMENT, SPEED_MILESTONE, MAX_PIPE_SPEED,
  HITBOX_INSET, INVINCIBILITY_MS, HS_STORAGE_KEY,
  state,
} from '../game.js';

describe('Task 1 — scaffold and config module', () => {
  beforeAll(async () => {
    await loadConfig();
    initConstants();
  });

  it('loadConfig() populates cfg from game-config.json', () => {
    expect(cfg).not.toBeNull();
    expect(cfg.physics.gravity).toBe(800);
    expect(cfg.pipes.gapSize).toBe(140);
    expect(cfg.storage.highScoreKey).toBe('flappyKiroHighScore');
  });

  it('initConstants() maps cfg values to exported constants', () => {
    expect(GRAVITY).toBe(800);
    expect(FLAP_VELOCITY).toBe(-300);
    expect(TERMINAL_VELOCITY).toBe(600);
    expect(BASE_PIPE_SPEED).toBe(120);
    expect(GAP_SIZE).toBe(140);
    expect(PIPE_SPACING).toBe(350);
    expect(GAP_MARGIN).toBe(60);
    expect(SPEED_INCREMENT).toBe(20);
    expect(SPEED_MILESTONE).toBe(5);
    expect(MAX_PIPE_SPEED).toBe(300);
    expect(HITBOX_INSET).toBe(8);
    expect(INVINCIBILITY_MS).toBe(1500);
    expect(HS_STORAGE_KEY).toBe('flappyKiroHighScore');
  });

  it('initial game state is MENU', () => {
    expect(state.gameState).toBe('MENU');
    expect(state.score).toBe(0);
    expect(state.pipes).toEqual([]);
    expect(state.particles).toEqual([]);
  });
});
