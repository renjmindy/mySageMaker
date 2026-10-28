# Contactor Log Validation Report

**Handler**: M6242 (from the 07/30 screenshots; the CSVs carry no handler ID)   **Side(s)**: front (1-256), rear (257-512)
**Period**: 2026-09-01 to 2026-10-02 (07/30 trial run excluded)   **Analyst**: Claude (draft)   **Reviewer**: [pending]
**Rules applied**: assumptions A1-A5, A7, A8, A15 (see `analysis-assumptions-log`); loader `lib/contactor_io.py`

## 1. Volume
| Side | Rows | Valid rows | Dropped (256) | Dropped (252-255) | Dropped (count-list gap > 50) | Dropped (N/A, count > 0) | Kept N/A + 0 (zero closed) |
|---|---|---|---|---|---|---|---|
| front | 11,632 | 11,276 | 146 | 171 | 9 | 30 | 488 |
| rear | 11,589 | 11,199 | 206 | 133 | 12 | 39 | 999 |

Overall failure rate: front 3.06%, rear 3.37%.

## 2. Noise (in kept readable rows)
| Side | Rows w/ out-of-range IDs | Rows w/ duplicate IDs | count != list |
|---|---|---|---|
| front | 27 (0.3%) | 248 (2.3%) | 1,132 (10.0%) of valid rows |
| rear | 179 (1.8%) | 32 (0.3%) | 756 (6.8%) of valid rows |

`err_01` is never below the list length, so list length is a **lower bound** on closures; availability is reported as a range (front 90.88-91.32%, rear 95.64-96.07%).

## 3. Flagged days (failure rate >= 5%)
Severity per `references/validation_rules.md`. "Evidence" is the day's cleaned availability against the period median (front 91.33%, rear 96.45%) and its robust z-score.

| Date | Side | Finding | Severity | Evidence | Decision |
|---|---|---|---|---|---|
| 2026-09-09 | front | 27.7% failed rows (57 near-full reads); coverage 65%; max gap 22 min | **CRITICAL** | cleaned availability 90.38%, z = -0.6 (normal); excluding the day moves the front headline by +0.01 pt | **KEEP WITH CAVEAT** (decided by process owner): state that 27.7% of the day's readings were unusable and coverage was 65% |
| 2026-09-08 | front | 10.3% failed | HIGH | 89.60%, z = -1.1 | Keep (proposed - confirm) |
| 2026-09-17 | front | 6.1% failed | HIGH | 89.31%, z = -1.3 | Keep (proposed - confirm) |
| 2026-09-03 | front | 5.3% failed | HIGH | 86.56%, z = -3.0 (lowest day, just under the 3.5 anomaly line) | Keep with caveat (proposed); check against a screenshot |
| 2026-09-18 | front | 5.07% failed (borderline; crossed 5% only after the gap rule) | HIGH | 87.51%, z = -2.4 | Keep (proposed - confirm) |
| 2026-09-08 | rear | 11.3% failed | HIGH | 94.85%, z = -0.7 | Keep (proposed - confirm) |
| 2026-09-09 | rear | 8.2% failed; **coverage 54%; 11 capture gaps of 16-90 min** (repeated outage) | HIGH | 94.92%, z = -0.6; gap time is not imputed (weight capped at 15 min) | Keep with caveat (proposed): report the repeated outage |
| 2026-09-03 | rear | 7.0% failed | HIGH | 93.93%, z = -1.1 | Keep (proposed - confirm) |
| 2026-09-17 | rear | 6.7% failed | HIGH | 93.11%, z = -1.4 | Keep (proposed - confirm) |
| 2026-09-20 | rear | 6.1% failed; 190 rows are `N/A` + 0 (zero closed, not failures) | HIGH | 97.97%, z = +0.6 | Keep; confirm the zero-closed stretch against a screenshot or the maintenance log |
| 2026-09-22 | rear | 5.1% failed | HIGH | 96.56%, z = 0.0 | Keep (proposed - confirm) |

Basis for "keep": failed rows are already excluded at row level, and the remaining readings on every flagged day look normal against neighbouring days. No flagged day is excluded outright. "Proposed" rows are my draft and need the reviewer's confirmation.

## 4. Exclusions handed to analysis
- Whole days excluded: **none**
- Row-level exclusions (applied by the loader): 256 and 252-255 counts, count - list gap > 50, `N/A` with count > 0
- Not analysed: 2026-07-30 trial run
- Caveats the analysis must carry: front 09/09 (27.7% unusable, 65% coverage); rear 09/09 (54% coverage, repeated capture gaps up to 90 min); 10/02 is a partial day (data ends 15:14)

## 5. Upstream fixes requested
- Capture owner: counts of 252-256 and "everything closed" readings look like screen-not-loaded failures; a validity flag at capture time would remove them.
- Capture owner: in about 7-10% of kept rows the count exceeds the list by around 10 - cause unknown, needs screenshots.
- 09/09 on both sides: investigate the repeated capture gaps (rear up to 90 min, front up to 22 min).

## 6. Open items
- A14: rows with count 240-251 whose list is also near-full (11 front, 17 rear) are kept; owner to confirm.
- Screenshot spot-check of front 09/09, rear 09/20 and one normal day: not done yet.
- The out-of-range token pattern is unexplained; compare with screenshots before attributing a cause.
