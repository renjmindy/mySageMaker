# Time-Series Patterns - Handler Contactor Availability

| Pattern | Looks like | Likely cause | Action |
|---|---|---|---|
| Level shift | availability steps up/down and stays | contactor fixed / failed, HIFIX change | find the closed-set change (closure-event-root-cause) |
| Single-day spike | one day far below neighbours | read artefacts (near-full 252-255), screen off | validate; exclude if artefact |
| Rear zero-closed days | rear closed = 0 for a whole day | board swapped or all repaired; or no-lot idle | confirm with process owner |
| Slow drift | gradual decline | wear accumulating | schedule preventive maintenance |
| Hour pattern | bump at fixed hours | lot starts/shift change | compare with run-state timeline (not yet available) |

Robust anomaly rule: `|0.6745 * (x - median) / MAD| > 3.5`.
