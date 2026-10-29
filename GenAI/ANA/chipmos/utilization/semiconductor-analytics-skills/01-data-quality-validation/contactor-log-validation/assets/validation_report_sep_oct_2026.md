# Contactor Log Validation Report

**Handler**: M6242 (from the 07/30 screenshots; the CSVs carry no handler ID)   **Side(s)**: front (1-256), rear (257-512)
**Period**: 2026-09-01 to 2026-10-21 (data ends 2026-10-21 18:24 front, 18:22 rear; 07/30 trial run excluded)   **Analyst**: Claude (draft)   **Reviewer**: [pending]
**Rules applied**: assumptions A1-A5, A7, A8, A15, A17 (see `analysis-assumptions-log`); loader `lib/contactor_io.py`. Open question A21 (a constant count-versus-list gap from 2026-10-05) is described in section 2.

## 1. Volume
| Side | Rows | Valid rows | Dropped (256) | Dropped (252-255) | Dropped (count-list gap > 50) | Dropped (N/A, count > 0) | Kept N/A + 0 (zero closed) |
|---|---|---|---|---|---|---|---|
| front | 17,498 | 17,008 | 212 | 217 | 28 | 33 | 548 |
| rear | 17,454 | 16,936 | 269 | 179 | 26 | 44 | 1,086 |

Overall failure rate: front 2.80%, rear 2.97%. The count-list gap rule dropped 9 front and 10 rear readings in September but 19 and 16 in October (9 and 7 of them on 2026-10-15); the October gap in section 2 is the likely reason, because a reading whose count is 40 above its list needs only 10 more to cross the limit of 50.

## 2. Noise (in kept readable rows)
| Side | Rows w/ out-of-range IDs | Rows w/ duplicate IDs | count != list |
|---|---|---|---|
| front | 319 (1.9%) | 553 (3.4%) | 5,665 (33.3%) of valid rows |
| rear | 1,479 (9.3%) | 78 (0.5%) | 4,949 (29.2%) of valid rows |

**Out-of-range (stray) numbers** (`site_id_validator.py`, by month): front 0.2% of readable rows in September, 4.7% in October (0.0% and 0.2% of all listed numbers); rear 1.8% and 20.9% (0.4% and 3.0% of listed numbers). They rise from 2026-10-05. The most common stray numbers are `0` on the front (287) and `1`, `0`, `37`, `43`, `4`, `7` on the rear; why they appear (an OCR split or merge) is not established. **Decision (process owner, 2026-10-29): ignore inaccurate site IDs on both sides (A17 confirmed)**; they explain only about 1% of the count-list gap below.

**Count above list, from 2026-10-05 (open question A21)** (`count_list_reconciler.py`, gap profile). Up to 2026-10-04 the count and the list differ by about 1 (front September: mean count 21.57 against mean list 20.61). From 2026-10-05 12:41 (front) and 12:43 (rear), about two thirds of valid readings show the count a **constant 40 above** everything listed (front 70.4%, rear 66.1%; the other values are 0 and, on the front, 25); October means are front 49.11 against 23.69 and rear 33.44 against 9.1. The two captures change within two minutes of each other. The data cannot say whether about 40 sites are closed on purpose (counted but not listed) or whether the list is cut off. **Decision (process owner, 2026-10-29): keep trusting the list length (A5)**; the lower bound, which counts the gap, is shown beside the headline in every deliverable until A21 is answered.

`err_01` is never below the list length. Availability is therefore reported as two figures: the list-based headline and the count-based lower bound (full period: front 90.85% and 86.19%, rear 95.99% and 91.46%).

## 3. Flagged days (failure rate >= 5%, or coverage < 75% on a day that is not the last)
Severity per `references/validation_rules.md`. "Evidence" is the day's cleaned availability (list-based) against the period median of the daily figures (front 91.24%, rear 96.33%) and its robust z-score.

| Date | Side | Finding | Severity | Evidence | Decision |
|---|---|---|---|---|---|
| 2026-09-09 | front | 27.7% failed rows (57 near-full reads); coverage 65%; max gap 22 min | **CRITICAL** | cleaned availability 90.38%, z = -0.5 (normal); excluding the day moves the front headline by about +0.01 pt | **KEEP WITH CAVEAT** (decided by process owner): state that 27.7% of the day's readings were unusable and coverage was 65% |
| 2026-09-08 | front | 10.3% failed | HIGH | 89.60%, z = -1.0 | Keep (proposed - confirm) |
| 2026-09-17 | front | 6.1% failed | HIGH | 89.31%, z = -1.1 | Keep (proposed - confirm) |
| 2026-09-03 | front | 5.3% failed | HIGH | 86.56%, z = -2.7 (flagged by the anomaly rule; also a high failure rate) | Keep with caveat (proposed); check against a screenshot |
| 2026-09-18 | front | 5.07% failed (borderline; crossed 5% only after the gap rule) | HIGH | 87.51%, z = -2.2 | Keep (proposed - confirm) |
| 2026-10-02 | front | **partial day**: readings stop at 15:14 and resume on 10-03; 246 readings, coverage 68%; the capture gap of about 9 hours is not counted (a reading never represents more than 15 minutes) | HIGH | 92.33%, z = +0.6 (normal) | **KEEP WITH CAVEAT** (decided by process owner, 2026-10-29): state that coverage was 68% |
| 2026-10-15 | front | 6.3% failed (6 reads of 256, 4 near-full, **9 dropped by the count-list gap rule**); coverage 83% | HIGH | 91.87%, z = +0.4 (normal) | **KEEP WITH CAVEAT** (decided by process owner, 2026-10-29): state that 6.3% of the day's readings were unusable |
| 2026-09-08 | rear | 11.3% failed | HIGH | 94.85%, z = -0.7 | Keep (proposed - confirm) |
| 2026-09-09 | rear | 8.2% failed; **coverage 54%; 11 capture gaps of 16-90 min** (repeated outage) | HIGH | 94.92%, z = -0.7; the last valid reading is carried forward across each gap, at most 15 min (A18) | Keep with caveat (proposed): report the repeated outage |
| 2026-09-03 | rear | 7.0% failed | HIGH | 93.93%, z = -1.1 | Keep (proposed - confirm) |
| 2026-09-17 | rear | 6.7% failed | HIGH | 93.11%, z = -1.5 | Keep (proposed - confirm) |
| 2026-09-20 | rear | 6.1% failed; 190 rows are `N/A` + 0 (zero closed, not failures) | HIGH | 97.97%, z = +0.8 | Keep; confirm the zero-closed stretch against a screenshot or the maintenance log |
| 2026-09-22 | rear | 5.1% failed | HIGH | 96.56%, z = +0.1 | Keep (proposed - confirm) |
| 2026-10-02 | rear | **partial day**: readings stop at 15:12 and resume on 10-03; coverage 68% | HIGH | 97.54%, z = +0.6 (normal) | **KEEP WITH CAVEAT** (decided by process owner, 2026-10-29): state that coverage was 68% |
| 2026-10-15 | rear | 5.6% failed (7 reads of 256, 3 near-full, **7 dropped by the count-list gap rule**); coverage 84% | HIGH | 92.03%, z = -2.0 | **KEEP WITH CAVEAT** (decided by process owner, 2026-10-29): state that 5.6% of the day's readings were unusable |

Basis for "keep": failed rows are already excluded at row level, and the remaining readings on every flagged day look normal against neighbouring days. No flagged day is excluded outright. "Proposed" rows are my draft and need the reviewer's confirmation. Days the anomaly rule flags for low availability without a data-quality cause (front 2026-10-08, z = -3.4, and 2026-10-14, z = -2.7, which is also at the 5% failure line) are analysis findings, not validation findings; see the analysis document.

## 4. Exclusions handed to analysis
- Whole days excluded: **none**
- Row-level exclusions (applied by the loader): 256 and 252-255 counts, count - list gap > 50, `N/A` with count > 0, out-of-range and duplicate IDs
- Not analysed: 2026-07-30 trial run
- Caveats the analysis must carry: front 09/09 (27.7% unusable, 65% coverage); rear 09/09 (54% coverage, repeated capture gaps up to 90 min); 10/02 on both sides (partial day, coverage 68%); 10/15 on both sides (5.6-6.3% unusable, 16 readings dropped by the gap rule); the count-above-list gap from 2026-10-05 (A21, open) and the rise in stray numbers from the same date

## 5. Upstream fixes requested
- Capture owner: counts of 252-256 and "everything closed" readings look like screen-not-loaded failures; a validity flag at capture time would remove them.
- Capture owner and process owner: **since 2026-10-05 about 12:41 the count is a constant 40 above the listed IDs on about two thirds of readings on both sides** - are about 40 sites closed on purpose, or is the list cut off? (A21)
- Capture owner: stray numbers (`0`, `1`, `37`, `43` ...) rise from the same date; ask whether anything in the capture changed.
- 09/09 on both sides: investigate the repeated capture gaps (rear up to 90 min, front up to 22 min).
- 10/02 on both sides: the capture stopped at about 15:12 and resumed after midnight.

## 6. Open items
- A21: the count-above-list gap from 2026-10-05 (owner to answer; both figures are shown meanwhile).
- A14: rows with count 240-251 whose list is also at least 240 (12 front, 26 rear) are kept; owner to confirm.
- Screenshot spot-check of front 09/09, rear 09/20, 10/15 and one normal day: not done yet.
- The stray-number pattern is unexplained; compare with screenshots before attributing a cause.
