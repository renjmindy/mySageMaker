# Ghosty Sprite Specification

## Overview

Ghosty is the player character in Flappy Kiro. The current asset (`assets/ghosty.png`) is a single 32×32px sprite. This document defines the full character specification including animation states, hitbox, and rendering behaviour.

---

## Sprite Dimensions

| Property | Value |
|---|---|
| Width | 32 px |
| Height | 32 px |
| Format | PNG (transparency required) |
| Scale | Rendered at 2× (64×64px on canvas) for visibility |

---

## Hitbox

Ghosty uses a **circular hitbox** centred on the sprite.

| Property | Value |
|---|---|
| Shape | Circle |
| Radius | 12 px (at 1× scale) / 24 px (at 2× render scale) |
| Centre X | sprite.x + 16 px (sprite midpoint) |
| Centre Y | sprite.y + 16 px (sprite midpoint) |

The hitbox is intentionally smaller than the sprite bounds to give the player a fair margin. At 2× render scale the effective radius is 24 px against a 64×64 px rendered sprite.

---

## Animation States

### Idle (MENU state)

Used on the start screen while waiting for input.

| Property | Value |
|---|---|
| Frames | 2 (frame 0, frame 1) |
| Frame duration | 400 ms each |
| Loop | Yes |
| Motion | Gentle vertical bob — offset `sin(t * 2) * 4` px |
| Sprite row | Row 0 (y: 0–31) |

```
Frame 0: neutral ghost face, eyes open
Frame 1: ghost face, eyes half-closed (blink)
```

### Flap (PLAYING state)

Used during active gameplay. Rotation is applied on top of the base sprite.

| Property | Value |
|---|---|
| Frames | 2 (frame 0, frame 1) |
| Frame duration | 100 ms each |
| Loop | Yes |
| Rotation | `clamp(vy * 3, -25°, 45°)` — tilts up on flap, down on fall |
| Sprite row | Row 0 (y: 0–31) — same frames as idle, rotation differentiates |

Rotation mapping:
- `vy < 0` (rising): rotate toward −25°
- `vy = 0` (level): 0°
- `vy > 0` (falling): rotate toward +45°

### Death (GAME_OVER transition)

Played once when a collision is triggered, before the game over screen appears.

| Property | Value |
|---|---|
| Frames | 3 (frame 0, frame 1, frame 2) |
| Frame duration | 80 ms each |
| Loop | No (holds on last frame) |
| Motion | Ghosty spins 360° over the 3-frame sequence |
| Sprite row | Row 1 (y: 32–63) — requires spritesheet update |

```
Frame 0: surprised expression (mouth open)
Frame 1: dizzy expression (X eyes)
Frame 2: faded/transparent ghost (opacity 0.5)
```

---

## Spritesheet Layout

The current `assets/ghosty.png` is a single frame. The target spritesheet layout for full animation support:

```
+----------+----------+----------+
| Idle 0   | Idle 1   |          |  ← Row 0 (y: 0)
| 32×32    | 32×32    |          |
+----------+----------+----------+
| Death 0  | Death 1  | Death 2  |  ← Row 1 (y: 32)
| 32×32    | 32×32    | 32×32    |
+----------+----------+----------+
```

Total spritesheet size: **96×64 px**

---

## Rendering Notes

- Sprite is drawn centred on Ghosty's physics position using `ctx.translate` + `ctx.rotate`
- `ctx.save()` / `ctx.restore()` wrap every Ghosty draw call to isolate the transform
- If `ghosty.png` fails to load, render a 32×32 white filled circle as fallback
- During the invincibility window at session start, Ghosty flashes at 100ms intervals (toggle `globalAlpha` between 1.0 and 0.4)

---

## Integration with game-config.json

The hitbox radius should be kept in sync with `game-config.json`:

```json
"collision": {
  "hitboxInset": 8
}
```

At 1× scale: effective radius = `(min(32, 32) / 2) - 8` = **8 px**  
At 2× render scale: effective radius = `(min(64, 64) / 2) - 8` = **24 px**

To use the explicit 12 px radius spec, set `hitboxInset` to `4` in `game-config.json`:  
`(32 / 2) - 4 = 12 px` at 1× scale.
