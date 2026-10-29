# Chart Selection - Handler Contactor Data

| Question | Form | Notes |
|---|---|---|
| Where are positions closed **now**? | 16-column grid heatmap in the handler's layout (highest row on top), one per side | default view = last 7 days; whole-period view on a toggle; single-hue sequential ramp |
| Which positions should be looked at first? | ranked table (position, location, last 7 days, whole period, status in plain words) | keyboard- and phone-friendly; the grid is the overview |
| How is capacity moving? | line, one y-axis, front vs rear | direct end labels + legend; band = plausible range of the period average; never dual axis |
| Headline number | tile with a plausible range and a lower bound | never a single exact figure from OCR-derived data |
| When did a group close or reopen? | event list from `closure-event-root-cause` | not drawn here |

Avoid: pie charts for open vs closed (always ~90/10), 3D, rainbow scales, one colour per position, a period-only map as the default view.
