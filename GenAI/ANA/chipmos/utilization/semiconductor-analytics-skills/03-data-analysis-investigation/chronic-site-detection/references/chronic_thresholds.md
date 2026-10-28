# Chronic-Site Thresholds

| Class | Closed share | Meaning |
|---|---|---|
| chronic | >= 50% | persistently down over the period - maintenance candidate |
| frequent | 10-50% | closed for part of the period (e.g. until a fix / after a fault) |
| occasional | < 10% | transient; mostly OCR/noise or short events |

## Recency status (last 7 days, A19)
| Status | Rule | Meaning |
|---|---|---|
| PERSISTENT | closed >= 50% of the last 7 days and of the days before | still broken, long-standing - top maintenance candidate |
| NEW | closed >= 50% of the last 7 days, < 20% before | recently broke - emerging, investigate cause |
| CURRENT | closed >= 50% of the last 7 days, otherwise | closed now |
| INTERMITTENT | closed 10-50% of the last 7 days | unstable, partly closed |
| RESOLVED | < 10% in the last 7 days but >= 10% over the period | fixed or gone - history only |

The window ends at the last valid reading (`--recent-days` changes it). On the rear side the period-chronic sites were not closed >= 50% in the last week, so the period class alone points at past problems.

Caveats
- A share of 30-50% with a sharp on/off boundary on a given day means the site was fixed or failed on that date - check `closure-event-root-cause`.
- Single-ID flicker (e.g. 91 vs 97 alternating) is OCR noise, not a closure.
- Aligned 2x2 blocks closing together (rows 2k-1,2k x cols 2j-1,2j) suggest a shared cause; confirm with the process owner (assumption A13).
