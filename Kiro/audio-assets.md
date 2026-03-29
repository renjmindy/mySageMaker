# Audio Assets Specification

## Overview

Flappy Kiro uses three in-game sound effects and one optional background music track. All sounds are loaded at startup with graceful silent fallback if any file is missing or fails to load.

Existing assets in `assets/`:
- `jump.wav` — flap sound (already present)
- `game_over.wav` — collision sound (already present)
- `score.wav` — score sound (needs to be created)
- `background.mp3` — background music (optional, needs to be created)

---

## Sound Effects

### Flap Sound

Triggered every time the player taps/clicks to make Ghosty flap.

| Property | Value |
|---|---|
| File | `assets/jump.wav` |
| Duration | 0.1 s |
| Character | Short whoosh — a quick upward air movement |
| Frequency profile | Starts mid-high (~800 Hz), sweeps up briefly then cuts off |
| Volume | 0.6 (relative to master) |
| Playback | Restarts from 0 on every flap — rapid tapping produces rapid sounds |
| Fallback | Silent — game continues normally |

Synthesis reference (Web Audio API):
```
OscillatorNode: type=sine, freq 600→900 Hz over 80ms
GainNode: attack 0ms, decay 80ms, sustain 0, release 20ms
```

---

### Score Sound

Triggered once each time Ghosty passes a pipe pair and the score increments.

| Property | Value |
|---|---|
| File | `assets/score.wav` |
| Duration | 0.2 s |
| Character | Pleasant chime — a clean, bright single note |
| Frequency profile | ~1046 Hz (C6), pure sine or light bell tone |
| Volume | 0.5 (relative to master) |
| Playback | Single play per score event, no restart needed |
| Fallback | Silent — game continues normally |

Synthesis reference:
```
OscillatorNode: type=sine, freq 1046 Hz (C6)
GainNode: attack 5ms, decay 150ms, sustain 0.1, release 50ms
Optional: second oscillator at 1318 Hz (E6) at 0.3 volume for warmth
```

---

### Collision Sound

Triggered once when Ghosty collides with a pipe or boundary, at the start of the collision animation.

| Property | Value |
|---|---|
| File | `assets/game_over.wav` |
| Duration | 0.3 s |
| Character | Soft thud — a muffled low impact, not harsh or jarring |
| Frequency profile | Low thump ~80–120 Hz with quick decay |
| Volume | 0.7 (relative to master) |
| Playback | Single play, does not restart |
| Fallback | Silent — game continues normally |

Synthesis reference:
```
OscillatorNode: type=sine, freq 100→40 Hz over 200ms (pitch drop)
GainNode: attack 0ms, decay 250ms, sustain 0, release 50ms
NoiseBuffer: short white noise burst at 0.2 volume for impact texture
```

---

## Background Music

Optional looping ambient track. Game runs normally if the file is absent.

| Property | Value |
|---|---|
| File | `assets/background.mp3` |
| Duration | 60–120 s (loops seamlessly) |
| Character | Retro chiptune or lo-fi ambient — upbeat but not distracting |
| Tempo | 120–140 BPM |
| Volume | 0.3 (relative to master, kept low under SFX) |
| Loop | Yes — seamless loop point at end of file |
| Playback | Starts when PLAYING state begins, pauses on PAUSE, stops on GAME_OVER |
| Fallback | Silent — game continues normally |

---

## Audio Manager Behaviour

| Event | Action |
|---|---|
| Flap | `playSound(jump)` — resets `currentTime = 0` before play |
| Score | `playSound(score)` — single play |
| Collision | `playSound(gameOver)` — single play at animation start |
| → PLAYING | `bgMusic.play()` (loop) |
| → PAUSED | `bgMusic.pause()` |
| PAUSED → PLAYING | `bgMusic.play()` (resumes from current position) |
| → GAME_OVER | `bgMusic.pause(); bgMusic.currentTime = 0` |

All play calls are wrapped in `.catch(() => {})` to suppress browser autoplay policy errors silently.

---

## File Format Requirements

| Property | Requirement |
|---|---|
| SFX format | WAV (PCM 16-bit, 44.1 kHz mono) |
| Music format | MP3 (128 kbps+, 44.1 kHz stereo) |
| Max SFX file size | 50 KB each |
| Max music file size | 5 MB |
