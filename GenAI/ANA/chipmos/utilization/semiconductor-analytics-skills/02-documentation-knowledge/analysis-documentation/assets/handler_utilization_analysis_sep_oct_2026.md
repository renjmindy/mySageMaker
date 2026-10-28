# Handler contactor utilization - Sep/Oct 2026

**Question**: How much of the handler's contactor capacity is usable, and where is it lost?
**Decision supported**: which contactor clusters to inspect or replace first. OEE is a later goal and is **blocked** (see Limitations).
**Author / date**: Claude (draft), 2026-10-28   **Reviewer**: [OPEN]   **Repo state**: commit `633f6b09` or later

## Data
- Source: Advantest handler *Contactor Select* screen logs, front (sites 1-256) and rear (257-512); catalog entry: `02-documentation-knowledge/handler-data-catalog/assets/contactor_logs_catalog_entry.md`.
- Period: 2026-09-01 to 2026-10-02 15:14 (2026-07-30 trial run excluded, A6). Raw data is private and not in the repository.
- Valid rows: front 11,276 of 11,632; rear 11,199 of 11,589. Failure rate (dropped readings): front 3.06%, rear 3.37%.
- Cleaning contract (A3, A4, A5, A8, A9, A15, A17, A18; defined once in `lib/contactor_io.py` and `02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml`): counts of 256 and 252-255 are read failures; a count exceeding the cleaned list by more than 50 is dropped; `N/A` with count 0 means zero closed; list length is trusted over the count; out-of-range and duplicate IDs are removed.
- Validation decisions per day: `01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md`. No whole day is excluded; front 09/09 is kept with a caveat (A16: 27.7% of its readings unusable, 65% coverage).

## Method
- Site availability = share of the 256 sites per side that are open, **time-weighted**: each valid reading represents the gap to the next one, capped at 15 minutes (A18): its state is carried forward across a dropped reading or a capture gap, up to that cap; dropped readings have no weight of their own.
- Range: the **upper bound** uses the cleaned list length as the number closed; the **lower bound** uses `max(err_01, list length)` because the reported count is never below the list (A5).
- Combined view (A12): mean of the front and rear figures, always shown next to the per-side numbers.
- Chronic site = closed in at least 50% of valid time over the period; clusters group neighbouring sites that are closed at least 10% of the time. A **recency status** (A19, last 7 days of data, to 2026-10-02) separates sites still closed now (PERSISTENT, NEW, CURRENT) from partly closed (INTERMITTENT) and fixed or gone (RESOLVED); the period figure alone can point at past problems.

## Results
| Side | Availability (upper) | Availability (lower) | 95% interval (day bootstrap) | Valid samples |
|---|---|---|---|---|
| front | **91.32%** | 90.88% | 90.57-92.08% | 11,276 |
| rear | **96.07%** | 95.64% | 95.30-96.83% | 11,199 |
| combined (mean of sides) | 93.70% | | | |

Precision: about +/-0.75 pt (daily standard deviation about 2.2 pts); the upper/lower range is narrower than this, so differences under about 1.5 pts between periods are not distinguishable from daily variation. The 252-255 rule is the one that moves the headline (+1.3 pts on the front); the gap rule moves it by about 0.01 pt; time-weighting versus a plain mean is worth about 0.6 pt.

- Daily range: front 86.56% (09/03) to 96.13% (09/16); rear 90.53% (09/05) to 99.68% (09/19).
- Chronic sites: front 17 of 256 (6.6%), rear 4 of 256 (1.6%). The ten worst sites account for 40.7% of front closure time and 44.1% of rear closure time.
- **Currently closed** (>= 50% of the last 7 days): front 20 of 256 (7.8%), rear 5 of 256 (2.0%).
- **Front**: over the period, four site clusters explain about 6.5 of the 8.7 points of lost capacity: sites 143/144/159/160/175/176/191/192 (2.67 pts), 197/198/213/214/229/230/245/246 (2.11 pts), 3/4/19/20 (1.21 pts) and 37/38/53/54/69/70 (0.51 pts). **The first three are still closed now** (3.03, 2.91 and 1.11 pts in the last 7 days; 16 sites PERSISTENT, and site 198 NEW, so the second cluster grew). The fourth is RESOLVED (0.19 pts in the last week).
- **Rear**: over the period the largest clusters are 463/464/479/480/495/496/510/511/512 (1.13 pts) and 291/292/306/307/308 (0.74 pts), **but neither is closed >= 50% of the last week** (INTERMITTENT, about 30% of the time); the four period-chronic rear sites were not chronic in both halves of the period. The cluster that needs attention now is 419/420/435/436, status **NEW**: 0.39 pts over the period but 1.53 pts in the last 7 days. Closed sets change between days (for example 479/463/480/464 on 09/21-22), so many rear closures are repairs or reconfigurations, not constant faults; read the rear period ranking as history.
- **Trend** (A20): no reliable level shift (best split 2026-09-12: front +1.08 pts, permutation p = 0.669; rear +1.91 pts, p = 0.112). The anomaly rule flagged 3 of 32 front days and 0 of 32 rear days; the front's lowest day, 09/03, also has a high failure rate (data quality first). Hour of day: 6 of 24 front hours and 8 of 24 rear hours look different from the same day's mean (about 1.1 expected by chance), but the pattern disappears (0 of 24 hours) once readings with 60 or more closed sites are excluded (99 front and 50 rear readings, 0.9% and 0.4% of valid). It is driven by these large-closure bursts, not a steady time-of-day effect; whether they are capture artefacts or real events is unknown. 32 days give low power: a level shift under about 2 pts would not be detected.
- Closed sites often form aligned 2x2 blocks (rows 2k-1,2k x columns 2j-1,2j). **This is a hypothesis (A13); the physical cause is not established.**

## Limitations and open items
- **OEE is blocked.** Time availability, Performance and Quality need run-state, output, good-unit and cycle-time data (A10, A11); none exist yet. Site availability here is a capacity factor, not OEE.
- The cost / impact estimate is **deferred** until real business parameters are supplied.
- Unconfirmed but applied rules: A9, A12, A17, A18, A19 (7-day recency window and status thresholds), A20 (time-series thresholds). Open: A11 (planned time basis), A13 (2x2 blocks), A14 (28 kept rows with counts 240-251 and a near-full list).
- Capture quality: 2026-09-09 has repeated capture gaps on both sides (rear up to 90 min); the cause of garbled site IDs is not established; no screenshot spot-check has been done yet.
- Metric owners and data owners are not yet named (`[OPEN]`).

## Reproduce
Run from the repository root with only `pandas` and `numpy` installed. `python 02-documentation-knowledge/analysis-documentation/scripts/doc_numbers_check.py` re-runs these commands and checks the numbers in this document.
```bash
python 01-data-quality-validation/contactor-log-validation/scripts/read_failure_detector.py
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side front
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side rear
python 03-data-analysis-investigation/downtime-time-series/scripts/daily_trend.py --side front
python 03-data-analysis-investigation/downtime-time-series/scripts/daily_trend.py --side rear
python 02-documentation-knowledge/semiconductor-metric-definitions/scripts/metric_yaml_validator.py --recompute
python 02-documentation-knowledge/analysis-assumptions-log/scripts/assumptions_tracker.py check
```
<!-- check-numbers: 3.06 | 3.37 | 11276 | 11199 | 91.32 | 90.88 | 96.07 | 95.64 | 93.70 | 17/256 | 4/256 | 6.6% | 1.6% | 2.67 | 2.11 | 1.21 | 0.51 | 1.13 | 0.74 | 40.7 | 44.1 | 0.669 | 0.112 | flagged 3 of 32 | flagged 0 of 32 | 6 of 24 | 8 of 24 | (99 readings, 0.9% of valid): 0 of 24 | (50 readings, 0.4% of valid): 0 of 24 | 90.57 | 92.08 | 95.30 | 96.83 | 20/256 | 5/256 | 3.03 | 2.91 | 1.11 | 1.53 | 0.19 | 86.56 | 96.13 | 90.53 | 99.68 | OK - log consistent -->
