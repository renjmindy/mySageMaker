// Tests for Task 2: localStorage high score module
import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import * as fc from 'fast-check';

const mockCfg = {
  physics:   { gravity: 800, jumpVelocity: -300, terminalVelocity: 600 },
  pipes:     { wallSpeed: 120, gapSize: 140, wallSpacing: 350, gapMargin: 60, speedIncrement: 20, speedMilestone: 5, maxWallSpeed: 300 },
  collision: { hitboxInset: 8, invincibilityMs: 1500 },
  visual:    { particleDuration: 500, scorePopupDuration: 700, collisionAnimMs: 500 },
  audio:     { bgMusicPath: 'assets/background.mp3' },
  storage:   { highScoreKey: 'flappyKiroHighScore' },
};

vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(mockCfg) })));

import { loadConfig, initConstants, readHighScore, writeHighScore, HS_STORAGE_KEY } from '../game.js';

// In-memory localStorage mock
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

vi.stubGlobal('localStorage', localStorageMock);

describe('Task 2 — localStorage high score module', () => {
  beforeAll(async () => {
    await loadConfig();
    initConstants();
  });

  beforeEach(() => {
    localStorage.clear();
  });

  // ── P18: High score is persisted to localStorage when beaten ────────────────
  it('P18: high score is persisted to localStorage when beaten', () => {
    // Feature: flappy-kiro, Property 18: High score is persisted to localStorage when beaten
    fc.assert(
      fc.property(
        fc.nat({ max: 10000 }),
        fc.nat({ max: 10000 }),
        (score, highScore) => {
          localStorage.clear();
          // Seed an existing high score
          localStorage.setItem(HS_STORAGE_KEY, String(highScore));

          if (score > highScore) {
            writeHighScore(score);
            const stored = parseInt(localStorage.getItem(HS_STORAGE_KEY), 10);
            return stored === score;
          } else {
            // No write — stored value should remain unchanged
            const stored = parseInt(localStorage.getItem(HS_STORAGE_KEY), 10);
            return stored === highScore;
          }
        }
      ),
      { numRuns: 200 }
    );
  });

  // ── P19: Corrupt or missing localStorage value defaults to 0 ────────────────
  it('P19: corrupt or missing localStorage value defaults to 0', () => {
    // Feature: flappy-kiro, Property 19: Corrupt or missing localStorage value defaults to 0
    const invalidValues = fc.oneof(
      fc.constant(null),                          // missing
      fc.constant(''),                            // empty string
      fc.constant('abc'),                         // non-numeric string
      fc.constant('-1'),                          // negative integer
      fc.constant('3.14'),                        // float string
      fc.constant('NaN'),                         // NaN string
      fc.string({ minLength: 1 }).filter(s => isNaN(parseInt(s, 10)) || parseInt(s, 10) < 0 || !Number.isInteger(parseFloat(s)))
    );

    fc.assert(
      fc.property(invalidValues, (badValue) => {
        localStorage.clear();
        if (badValue !== null) {
          localStorage.setItem(HS_STORAGE_KEY, badValue);
        }
        // readHighScore must return 0 for any invalid/missing value
        const result = readHighScore();
        if (result !== 0) return false;

        // And must overwrite the corrupt entry with '0'
        const stored = localStorage.getItem(HS_STORAGE_KEY);
        return stored === '0';
      }),
      { numRuns: 200 }
    );
  });

  // ── Unit: valid integer round-trips correctly ────────────────────────────────
  it('readHighScore() returns the stored non-negative integer', () => {
    fc.assert(
      fc.property(fc.nat({ max: 100000 }), (n) => {
        localStorage.clear();
        localStorage.setItem(HS_STORAGE_KEY, String(n));
        return readHighScore() === n;
      }),
      { numRuns: 200 }
    );
  });

  it('readHighScore() returns 0 when key is absent', () => {
    expect(readHighScore()).toBe(0);
  });

  it('writeHighScore() stores the score as a string under HS_STORAGE_KEY', () => {
    writeHighScore(42);
    expect(localStorage.getItem(HS_STORAGE_KEY)).toBe('42');
  });
});
