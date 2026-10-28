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
