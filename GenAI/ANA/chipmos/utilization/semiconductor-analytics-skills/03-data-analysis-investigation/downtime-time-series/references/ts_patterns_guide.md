# Time-Series Patterns - Handler Contactor Availability

| Pattern | Looks like | Likely cause | Action |
|---|---|---|---|
| Level shift | availability steps up/down and stays | contactor fixed / failed, HIFIX change | find the closed-set change (closure-event-root-cause) |
| Single-day spike | one day far below neighbours | read artefacts (near-full 252-255), screen off | validate; exclude if artefact |
| Rear zero-closed days | rear closed = 0 for a whole day | board swapped or all repaired; or no-lot idle | confirm with process owner |
| Slow drift | gradual decline | wear accumulating | schedule preventive maintenance |
| Hour pattern | bump at fixed hours | lot starts/shift change | compare with run-state timeline (not yet available) |

Robust anomaly rule: `|0.6745 * (x - median) / MAD| > 2.5` (A20). A threshold of 3.5 would need a deviation of 5.7 pts (front) / 8.3 pts (rear) from the median and fires on nothing in Sep-Oct 2026; at 2.5 the front flags 3 of 32 days (0.4 expected by chance) and the rear 0.

A day that is flagged *and* has a high failure rate is a data-quality candidate first (front 09/03: lowest day, 5.3% failed readings).

## Evaluation record (Sep-Oct 2026)
| Check | Front | Rear |
|---|---|---|
| daily series equals `site_availability.py` | exact | exact |
| days flagged at z 3.5 / 3.0 / 2.5 / 2.0 | 0 / 0 / 3 / 5 | 0 / 0 / 0 / 1 |
| best level shift (split 2026-09-12), permutation p | +1.08 pts, p = 0.669 | +1.91 pts, p = 0.112 |
| hours beyond 2 SE (within-day test) | 6 of 24 | 8 of 24 |
| same, without readings of >= 60 closed sites | 0 of 24 (99 readings, 0.9%) | 0 of 24 (50 readings, 0.4%) |

Conclusion: no reliable level shift; no steady time-of-day effect - the apparent hour pattern comes from a small number of large-closure bursts (lowest hours about 2-3, 6-8, 21). Whether those bursts are capture artefacts or real events needs run-state data or screenshots.

Caveats: days are treated as exchangeable in the shift test (no autocorrelation model); 32 days give low power, so a shift under about 2 pts would not be detected.
