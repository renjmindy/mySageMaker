# Handler contactor utilization - Sep/Oct 2026

**Question**: How much of the handler's contactor capacity is usable, and where is it lost?
**Decision supported**: which contactor clusters to inspect or replace first. OEE is a later goal and is **blocked** (see Limitations).
**Author / date**: Claude (draft), 2026-10-29   **Reviewer**: [OPEN]   **Repo state**: commit `5eca233a` or later

## Data
- Source: Advantest handler *Contactor Select* screen logs, front (sites 1-256) and rear (257-512); catalog entry: `02-documentation-knowledge/handler-data-catalog/assets/contactor_logs_catalog_entry.md`.
- Period: 2026-09-01 to 2026-10-21 18:24 (51 days; 2026-07-30 trial run excluded, A6). Raw data is private and not in the repository.
- Valid rows: front 17,008 of 17,498; rear 16,936 of 17,454. Failure rate (dropped readings): front 2.80%, rear 2.97%.
- Cleaning contract (A3, A4, A5, A8, A9, A15, A17, A18; defined once in `lib/contactor_io.py` and `02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml`): counts of 256 and 252-255 are read failures; a count exceeding the cleaned list by more than 50 is dropped; `N/A` with count 0 means zero closed; **list length is trusted over the count (A5, reaffirmed 2026-10-29)**; out-of-range and duplicate IDs are removed (**A17, confirmed for both sides 2026-10-29**).
- Validation decisions per day: `01-data-quality-validation/contactor-log-validation/assets/validation_report_sep_oct_2026.md`. No whole day is excluded; front 09/09 (27.7% unusable, 65% coverage), 10/02 on both sides (partial day, 68% coverage) and 10/15 on both sides (5.6-6.3% unusable) are kept with a caveat.

## Method
- Site availability = share of the 256 sites per side that are open, **time-weighted**: each valid reading counts for the time until the next reading in the file, capped at 15 minutes (A18). A dropped reading's own time is not counted; across a capture gap (missing rows) the last valid reading is carried forward for at most 15 minutes.
- **Two figures are always shown.** The **list-based figure** (the headline) uses the cleaned list length as the number closed. The **count-based lower bound** uses `max(err_01, list length)`, because the reported count is never below the list (A5). They were within 0.5 pt of each other until 2026-10-04; since then they are far apart (open question A21, below).
- Combined view (A12): mean of the front and rear figures, always shown next to the per-side numbers.
- Chronic site = closed in at least 50% of valid time over the period; clusters group neighbouring sites that are closed at least 10% of the time. A **recency status** (A19, last 7 days of data, to 2026-10-21) separates sites still closed now (PERSISTENT, NEW, CURRENT) from partly closed (INTERMITTENT) and fixed or gone (RESOLVED); the period figure alone can point at past problems.

## Results (2026-09-01 to 2026-10-21)
| Side | Availability, list-based (headline) | Availability, count-based lower bound | 95% interval of the headline (day bootstrap) | Valid samples |
|---|---|---|---|---|
| front | **90.85%** | 86.19% | 90.25-91.43% | 17,008 |
| rear | **95.99%** | 91.46% | 95.45-96.53% | 16,936 |
| combined (mean of sides, list-based) | 93.42% | | | |

**Before and after 2026-10-05** (same commands with `--end 2026-10-04` and `--start 2026-10-05`):

| Period | Front: list-based / lower bound | Rear: list-based / lower bound |
|---|---|---|
| 2026-09-01 to 2026-10-04 | 91.30% / 90.86% | 96.06% / 95.63% |
| 2026-10-05 to 2026-10-21 | 89.97% / 77.00% | 95.86% / 83.44% |

Precision: the interval is about +/-0.6 pt (daily standard deviation about 2 pts), but the list-based and count-based figures now differ by about 4.7 pts on the front (90.85 against 86.19) and 4.5 pts on the rear (95.99 against 91.46), and by 13 and 12 pts since 2026-10-05. The open question below is therefore a larger uncertainty than sampling. Differences under about 1.5 pts between periods are not distinguishable from daily variation. **Cleaning rules**: the confirmed rules (252-255 counts and the count-list gap) raise the front headline from 89.95% with only the 256 rule to 90.85% (the 252-255 rule is worth 0.77 pt of that and the gap rule 0.12 pt), and the rear from 95.80% to 95.99%; time-weighting against a plain mean is worth 0.65 pt on the front (90.85% against 91.50%) and 0.53 pt on the rear (95.99% against 96.52%). Rule and weighting sensitivities are in `03-data-analysis-investigation/site-availability/references/availability_method.md`.

- Daily range (list-based): front 85.46% (10/08) to 96.13% (09/16); rear 90.53% (09/05) to 99.68% (09/19).
- Chronic sites: front 17/256 (6.6%), rear 4/256 (1.6%). The ten worst sites account for 39.2% of front closure time and 38.7% of rear closure time.
- **Currently closed** (>= 50% of the last 7 days): front 21/256 (8.2%), rear 9/256 (3.5%).
- **Front**: the largest clusters are sites 143/144/159/160/175/176/191/192 (2.73 pts over the period, 2.64 pts in the last 7 days, PERSISTENT) and 197/198/213/214/229/230/245/246 (2.24 pts; 2.52 pts in the last 7 days, CURRENT and PERSISTENT). A newer group 125/141/157/173/189 is closed now (0.52 pts over the period, 1.15 pts in the last 7 days; CURRENT and NEW); its five sites are all in column 13 (rows 8-12), not a 2x2 block. The block 3/4/19/20 (1.00 pts over the period) is **no longer closed now** (0.50 pts in the last 7 days, INTERMITTENT), and 37/38/53/54/69/70 (0.49 pts) has 0 of 6 closed now. The ranking repeats across the two halves of the period: top-20 overlap 17/20.
- **Rear**: 463/464/479/480/495/496/511/512 is the largest cluster over the period (0.96 pts) and 4 of its 8 sites (463/464/479/480) are closed now (1.24 pts in the last 7 days, CURRENT). A new group 381/397/413/429/445 (status NEW) is closed now (0.44 pts over the period, 1.08 pts in the last 7 days); its five sites are all in column 13 (rows 24-28). The earlier new group 419/420/435/436 has resolved (0.29 pts over the period, 0.04 pts in the last week). Only 8 of the top 20 sites repeat across halves of the period (top-20 overlap 8/20; chronic in both halves: both 0), so read the rear period ranking as history and the closed-now list as the current picture. Closed sets change between days, so many rear closures are repairs or reconfigurations, not constant faults.
- **Window sensitivity** (A19): the number closed now depends on the window. Front 17/256 (3 days), 21/256 (7 days) and 25/256 (14 days); rear 4/256, 9/256 and 10/256. The two big front clusters cost 3.10 and 3.09 pts (3 days) or 2.76 and 2.55 pts (14 days); the newer front group 0.78 pts (3 days, INTERMITTENT) or 1.37 pts (14 days). The rear block 463/464/479/480 costs 1.56 pts (3 days) or 1.02 pts (14 days), and the rear column-13 group 0.73 pts (3 days, INTERMITTENT) or 1.28 pts (14 days). The window changes how large and how current a group looks; it does not change which groups exist.
- **Trend** (A20): no reliable level shift (front best split 2026-10-08, permutation p = 0.227; rear best split 2026-09-12, p = 0.216). The anomaly rule flagged 4 of 51 front days and 1 of 51 rear days; the front's flagged days 09/03 and 10/14 also have a high failure rate (data quality first). Hour of day: 4 of 24 hours look different from the same day's mean on each side (about 1.1 expected by chance), and the pattern disappears (0 of 24 hours) once readings with 60 or more closed sites are excluded ((153 readings, 0.9% of valid): 0 of 24 on the front; (97 readings, 0.6% of valid): 0 of 24 on the rear). It is driven by large-closure bursts, not a steady time-of-day effect; whether they are capture artefacts or real events is unknown. 51 days give low power: a level shift under about 2 pts would not be detected.
- Closed sites often form aligned 2x2 blocks (rows 2k-1,2k x columns 2j-1,2j). **This is a hypothesis (A13); the physical cause is not established.** The two five-site groups in column 13 are not 2x2 blocks; no cause is established for them either.

## What changed on 2026-10-05 (open question A21)
Until 2026-10-04 the reported count of closed sites and the number of listed site IDs agreed within about 1 (front September: mean count 21.57 against a mean list of 20.61). From **2026-10-05 12:41 (front) and 12:43 (rear)** the count is a **constant 40 above** everything listed on about two thirds of valid readings (front 70.4%, rear 66.1%); the other readings mostly show a gap of 0 (on the front, often 25). October means: front 49.11 against a mean list of 23.69; rear 33.44 against a mean list of 9.1. The most common gap values after the start are 40 (2491) on the front and 40 (1728) on the rear.

- **Open question for the process owner and the capture owner**: are about 40 sites closed on purpose (for example a different setup), so they are counted but not listed, or is the list cut off by the capture? The data cannot say.
- **Decision for now (process owner, 2026-10-29)**: trust the list length (A5), so the headline is the list-based figure; show the count-based lower bound beside it everywhere.
- What it does to the numbers: since 2026-10-05 the lower bound is 13 pts (front) and 12 pts (rear) below the list-based figure (table above). The count-list gap rule also dropped more readings (19 front and 16 rear in October against 9 and 10 in September).
- **Stray numbers** (out-of-range IDs) rise from the same date: front 0.2% of readable rows in September and 4.7% in October (0.0% and 0.2% of all listed numbers); rear 1.8% and 20.9% (0.4% and 3.0% of listed numbers). They are removed (A17, confirmed 2026-10-29) and explain only about 1% of the gap above; the cause is not established.

## Limitations and open items
- **OEE is blocked.** Time availability, Performance and Quality need run-state, output, good-unit and cycle-time data (A10, A11); none exist yet. Site availability here is a capacity factor, not OEE.
- The cost / impact estimate is **deferred** until real business parameters are supplied.
- Unconfirmed but applied rules: A9, A12, A18, A19 (7-day recency window and status thresholds), A20 (time-series thresholds). Open: A11 (planned time basis), A13 (2x2 blocks), A14 (12 front and 26 rear kept rows with counts 240-251 and a near-full list), **A21 (the 40-site gap)**.
- Capture quality: 2026-09-09 has repeated capture gaps on both sides (rear up to 90 min); 2026-10-02 is a partial day on both sides (readings stop at about 15:12 and resume after midnight); the cause of garbled site IDs and of the October changes is not established; no screenshot spot-check has been done yet.
- Metric owners and data owners are not yet named (`[OPEN]`).

## Reproduce
Run from the repository root with only `pandas` and `numpy` installed. `python 02-documentation-knowledge/analysis-documentation/scripts/doc_numbers_check.py` re-runs these commands and checks the numbers in this document.
```bash
python 01-data-quality-validation/contactor-log-validation/scripts/read_failure_detector.py
python 01-data-quality-validation/contactor-log-validation/scripts/count_list_reconciler.py
python 01-data-quality-validation/contactor-log-validation/scripts/site_id_validator.py
python 05-stakeholder-communication/analysis-qa-checklist/scripts/qa_runner.py --data-only
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days --end 2026-10-04
python 03-data-analysis-investigation/site-availability/scripts/site_availability.py --quiet-days --start 2026-10-05
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side front
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side rear
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side front --recent-days 3
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side front --recent-days 14
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side rear --recent-days 3
python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side rear --recent-days 14
python 03-data-analysis-investigation/downtime-time-series/scripts/daily_trend.py --side front
python 03-data-analysis-investigation/downtime-time-series/scripts/daily_trend.py --side rear
python 02-documentation-knowledge/semiconductor-metric-definitions/scripts/metric_yaml_validator.py --recompute
python 02-documentation-knowledge/analysis-assumptions-log/scripts/assumptions_tracker.py check
```
<!-- check-numbers: 2.80 | 2.97 | 17008 | 16936 | 90.85 | 86.19 | 95.99 | 91.46 | 93.42 | 90.25 | 91.43 | 95.45 | 96.53 | 91.30 | 90.86 | 96.06 | 95.63 | 89.97 | 77.00 | 95.86 | 83.44 | 2026-10-05 12:41 | 2026-10-05 12:43 | 70.4% | 66.1% | 21.57 vs mean list 20.61 | 49.11 vs mean list 23.69 | 33.44 vs mean list 9.1 | 40 (2491) | 40 (1728) | 4.7% of readable rows, 0.2% of all listed numbers | 20.9% of readable rows, 3.0% of all listed numbers | 0.2% of readable rows, 0.0% of all listed numbers | 1.8% of readable rows, 0.4% of all listed numbers | 17/256 | 4/256 | 6.6% | 1.6% | 21/256 | 9/256 | 25/256 | 10/256 | 8.2% | 3.5% | 39.2 | 38.7 | 2.73 | 2.64 | 2.24 | 2.52 | 1.00 | 0.50 | 0.52 | 1.15 | 0.49 | 0.96 | 1.24 | 0.44 | 1.08 | 0.29 | top-20 overlap 17/20 | top-20 overlap 8/20 | both 0 | 3.10 | 3.09 | 2.76 | 2.55 | 0.78 | 1.37 | 1.56 | 1.02 | 0.73 | 1.28 | 0.227 | 0.216 | flagged 4 of 51 | flagged 1 of 51 | 4 of 24 | (153 readings, 0.9% of valid): 0 of 24 | (97 readings, 0.6% of valid): 0 of 24 | 85.46 | 96.13 | 90.53 | 99.68 | 89.95% (256-only) -> 90.85% (confirmed rules) | 95.80% (256-only) -> 95.99% (confirmed rules) | 90.85% vs 91.50% | 95.99% vs 96.52% | OK - log consistent -->
