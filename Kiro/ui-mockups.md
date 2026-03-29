# UI Mockups

## Overview

All UI is rendered on the HTML5 Canvas. There are no DOM elements outside the canvas itself. Layouts below use ASCII art to show relative positioning. All coordinates are expressed as percentages of canvas dimensions for responsiveness.

---

## Main Menu (MENU state)

```
┌─────────────────────────────────────────┐
│                                         │
│         ~ ~ clouds ~ ~                  │
│                                         │
│         ┌─────────────────┐             │
│         │   FLAPPY KIRO   │  ← title    │
│         │   (large font)  │             │
│         └─────────────────┘             │
│                                         │
│              [Ghosty]                   │  ← idle float animation
│           (bobbing gently)              │
│                                         │
│         ┌─────────────────┐             │
│         │   Best: 42      │  ← high score (prominent)
│         └─────────────────┘             │
│                                         │
│      Press SPACE or tap to play         │  ← start prompt (pulsing)
│                                         │
├─────────────────────────────────────────┤
│  Score: 0  │  Best: 42                  │  ← score bar (always visible)
└─────────────────────────────────────────┘
```

### Layout Details

| Element | Position | Style |
|---|---|---|
| Title "FLAPPY KIRO" | 50% x, 28% y | Large bold font, white with dark shadow |
| Ghosty sprite | 50% x, 48% y | 2× scale, idle bob animation |
| High score | 50% x, 62% y | Medium font, white, labelled "Best:" |
| Start prompt | 50% x, 75% y | Small font, white, opacity pulses 0.5→1.0 at 1s interval |
| Score bar | bottom strip, full width, ~40px tall | Dark semi-transparent background |

Note: No separate "Play" or "High Scores" buttons — the entire canvas is the tap target to start. This matches the single-input design of the game.

---

## In-Game HUD (PLAYING state)

```
┌─────────────────────────────────────────┐
│  ~ ~ clouds (parallax) ~ ~              │
│                                         │
│  ║         ║      ║         ║           │  ← pipes
│  ║         ║      ║         ║           │
│  ║         ║      ║         ║           │
│             gap    gap                  │
│                  +1  ← score popup      │
│         👻  ← Ghosty + particle trail   │
│  ║         ║      ║         ║           │
│  ║         ║      ║         ║           │
│                                         │
├─────────────────────────────────────────┤
│  Score: 7  │  Best: 42                  │  ← score bar
└─────────────────────────────────────────┘
```

### Layout Details

| Element | Position | Style |
|---|---|---|
| Score bar | bottom strip, full width, ~40px tall | Dark semi-transparent background |
| Current score | score bar left ~20px | Medium bold font, white, labelled "Score:" |
| High score | score bar right ~20px | Medium font, white, labelled "Best:" |
| Score popup "+1" | near top-centre of play area | White text, floats up 40px and fades over 700ms |
| Particle trail | behind Ghosty | Small translucent circles, fade over 500ms |

---

## Pause Overlay (PAUSED state)

```
┌─────────────────────────────────────────┐
│  ~ ~ clouds still moving ~ ~            │
│                                         │
│  ║         ║      ║         ║           │  ← frozen pipes
│  ║         ║      ║         ║           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │  ← semi-transparent overlay
│  │                                   │  │
│  │           ⏸  PAUSED              │  │
│  │                                   │  │
│  │   Press ESC or P to resume        │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│                                         │
├─────────────────────────────────────────┤
│  Score: 7  │  Best: 42                  │
└─────────────────────────────────────────┘
```

### Layout Details

| Element | Position | Style |
|---|---|---|
| Overlay | full canvas | `rgba(0, 0, 0, 0.45)` fill |
| "PAUSED" text | 50% x, 45% y | Large bold font, white |
| Resume prompt | 50% x, 58% y | Small font, white |
| Clouds | continue scrolling | Unaffected by pause |
| Pipes + Ghosty | frozen | No movement while paused |

---

## Game Over Screen (GAME_OVER state)

```
┌─────────────────────────────────────────┐
│  ~ ~ clouds ~ ~                         │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │                                   │  │
│  │         GAME OVER                 │  │
│  │                                   │  │
│  │   Score:    12                    │  │
│  │   Best:     42                    │  │
│  │                                   │  │
│  │   ✨ NEW BEST! ✨  (if beaten)    │  │
│  │                                   │  │
│  │   Press SPACE or tap to restart   │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│                                         │
├─────────────────────────────────────────┤
│  Score: 12  │  Best: 42                 │
└─────────────────────────────────────────┘
```

### Layout Details

| Element | Position | Style |
|---|---|---|
| Overlay | full canvas | `rgba(0, 0, 0, 0.55)` fill |
| "GAME OVER" | 50% x, 32% y | Large bold font, white |
| Final score | 50% x, 44% y | Medium font, white, labelled "Score:" |
| High score | 50% x, 52% y | Medium font, white, labelled "Best:" |
| "NEW BEST!" | 50% x, 60% y | Medium font, gold/yellow, only shown when score = new high score |
| Restart prompt | 50% x, 72% y | Small font, white, opacity pulses 0.5→1.0 |
| Score bar | bottom strip | Shows updated high score immediately |

---

## Score Bar (persistent across all states)

```
┌─────────────────────────────────────────┐
│  Score: 7                    Best: 42   │
└─────────────────────────────────────────┘
```

| Property | Value |
|---|---|
| Height | 40 px |
| Background | `rgba(30, 30, 40, 0.85)` |
| Font | Bold, 18px, white |
| Score label | Left-aligned, 20px from left edge |
| Best label | Right-aligned, 20px from right edge |
| Visible | Always — all four game states |

---

## Typography

| Use | Font | Size | Weight | Colour |
|---|---|---|---|---|
| Title | System sans-serif | 42px | 900 | White + 2px dark shadow |
| Game Over heading | System sans-serif | 36px | 700 | White |
| Score values | System sans-serif | 24px | 700 | White |
| Prompts | System sans-serif | 16px | 400 | White (pulsing opacity) |
| Score bar | System sans-serif | 18px | 700 | White |
| Score popup "+1" | System sans-serif | 20px | 700 | White |
| New Best | System sans-serif | 22px | 700 | `#FFD700` (gold) |
