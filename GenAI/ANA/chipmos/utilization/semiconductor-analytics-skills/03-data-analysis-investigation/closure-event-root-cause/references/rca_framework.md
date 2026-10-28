# RCA Framework - Contactor Closure Events

| Hypothesis | Evidence for | Evidence against | Test |
|---|---|---|---|
| Single contactor failure | 1 site, persists, no neighbours | neighbours change too | compare with contact-resistance / retest data |
| Module / board issue | aligned 2x2 (or larger) block closes together | scattered sites | inspect board map; check if block opens after a board swap |
| Handler fault / setup change | many sites change at the same minute; both sides | one side only | compare with Alarm / setup change history |
| Capture/OCR artefact | count 252-256, IDs out of range, flicker of one ID | stable set over hours | check screenshots; exclude |
| Planned reconfiguration | closed set equals the sites not needed for the lot (e.g. trial: 1-64 only) | closed set tied to faults | check lot / device change |

Always: (1) timeline, (2) both sides, (3) maintenance log, (4) one change at a time.

## Reading the `block_aligned` column
`block_aligned` = share of event sites whose complete aligned 2x2 block closed/opened with them.
- ~1.0 -> module/board-style event (e.g. rear 463/464/479/480) - prioritise for physical inspection
- ~0.0 with many blocks -> scattered sites - suspect capture noise or a transient handler condition; verify against screenshots before acting

## Evaluation record (Sep-Oct 2026)
Detection was tested by injecting known closures into quiet sites of the real cleaned data (12 trials per case):
| Injected | Rear | Front |
|---|---|---|
| single site, 2 readings (~8 min) | 0 of 12 (ignored by design) | 0 of 12 |
| single site, 3 to 45 readings (~12 min to 3 h) | 12 of 12 | 12 of 12 |
| 2x2 block, 3 h, found as an aligned event | 12 of 12 | 12 of 12 (was 8 of 12 when events were grouped by time only) |

Output size on the real data (consistent readings, defaults): rear 791 episodes -> 504 spatially separate events -> 67 with >= 4 sites and >= 30 min (58 aligned >= 0.9, 6 scattered < 0.3); front 1,234 -> 682 -> 87. Earlier time-only grouping produced 138 rear and 217 front events with >= 4 sites, mostly scattered.

False-event baseline: sites closed < 0.5% of the time still show about 1.4 episodes each (median about 55 min) - short closures of healthy sites, real or noise. A random set of 8 sites scores a block alignment of about 0, so aligned events are real signal; scattered ones are unexplained.

Not tested: agreement with real maintenance history (no log exists); timing accuracy on real data. Start times are exact on synthetic data.

