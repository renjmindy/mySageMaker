# Insight Brief - handler contactor capacity, 2026-09-01 to 2026-10-02

**Headline**: front 91.32% of positions able to test (lower bound 90.88%), rear 96.07% (lower bound 95.64%). Source: `02-documentation-knowledge/analysis-documentation/assets/handler_utilization_analysis_sep_oct_2026.md`; assumptions: `02-documentation-knowledge/analysis-assumptions-log/assumptions.json`.

## Insights
Ranked by the score in the table below. "Closed" means a test position that cannot test. No cause is stated as fact: the physical explanation for neighbouring groups failing together is a hypothesis (A13).

| # | Insight | Evidence | Confidence | Depends on | Action |
|---|---|---|---|---|---|
| 1 | Three groups of front positions are closed now and account for most of the current front loss. | In the last 7 days: 3.03 pts (sites 143/144/159/160/175/176/191/192), 2.91 pts (197/198/213/214/229/230/245/246) and 1.11 pts (3/4/19/20), 7.05 pts together. 20 of 256 front sites (7.8%) are closed now, 16 of them PERSISTENT. With a 3- or 14-day window the same three groups cost 3.01/2.82/1.37 pts and 2.72/2.49/1.04 pts. | **High** - the ranking repeats across both halves of the period (top-20 overlap 17/20), the groups are still closed now, and the result is insensitive to the window length (3, 7 or 14 days). | A8 (CONFIRMED), A15 (CONFIRMED), A19 (APPLIED) | Inspect the three front groups first. That neighbouring positions fail together suggests a shared part, but this is a hypothesis. |
| 2 | One rear group of four positions broke recently and is the main rear problem now; the older rear groups are only partly closed. | Sites 419/420/435/436 are NEW: 0.39 pts over the period but 1.53 pts in the last 7 days (1.51 pts with a 3-day window, 0.82 pts with 14 days). The older groups 463/464/479/480 and 291/292/307/308 are closed about 30% of the last week. 5 of 256 rear sites (2.0%) are closed now; no rear site was chronic in both halves (top-20 overlap 13/20). | **Medium** - the group exists under every window, but its size depends on the window (1.5 to 0.8 pts) and rests on about two weeks of data. | A19 (APPLIED) | Inspect the new rear group next. Treat the rear period ranking as history, not as a list of current problems. |
| 3 | The headline depends on how unreadable screen readings are handled, and the confirmed rules matter. | The confirmed rule that also drops counts of 252-255 raises the front headline by 1.3 pts compared with counting only 256 as a failed reading. The count-versus-list rule moves the headline by about 0.01 pt. 3.06% of front and 3.37% of rear readings are unusable; on front 09/09, 27.7% of readings were unusable. | **High** - measured directly on the data; the two rules that matter are confirmed, and the applied ones are insensitive (the gap rule changes the headline by about 0.01 pt). | A8 (CONFIRMED), A15 (CONFIRMED), A9 (APPLIED), A17 (APPLIED) | Ask the capture owner for a validity flag on every screen reading. Keep the confirmed rules. |
| 4 | OEE cannot be reported yet. | Only the share of positions able to test is measured. Run and idle time, output, good-unit and cycle-time data do not exist in the project. | **High** - a fact about the available data, not an estimate. | A10 (CONFIRMED) | Obtain run and idle time, output, good-unit and cycle-time data, and name owners for each feed. |
| 5 | No reliable trend and no steady time-of-day pattern; the apparent hour pattern comes from a small number of bursts. | Best level shift (2026-09-12): front +1.08 pts (p = 0.669), rear +1.91 pts (p = 0.112). Daily standard deviation about 2.2 pts; plausible range front 90.57-92.08%, rear 95.30-96.83%. 6 of 24 front hours and 8 of 24 rear hours stand out (about 1.1 expected by chance), but 0 of 24 once readings with 60 or more closed sites are excluded (99 front, 50 rear readings). | **Medium** - 32 days give low power, so a shift under about 2 pts would not be detected; thresholds are analyst choices. | A20 (APPLIED), A18 (APPLIED) | Do not act on month-to-month changes under about 1.5 pts. Re-test with three months of data. Check the burst hours (about 2-3, 6-8 and 21) against run-state data or screenshots. |

## Scoring
Scales are defined in `references/prioritization_guide.md`. Score = impact x confidence x actionability.

| # | Impact | Confidence | Actionability | Score | Rationale |
|---|---|---|---|---|---|
| 1 | 3 | 3 | 3 | 27 | 7.05 pts closed now; High; aligned groups, a targeted inspection |
| 2 | 2 | 2 | 3 | 12 | 1.53 pts closed now; Medium; one aligned four-site group |
| 3 | 2 | 3 | 2 | 12 | moves the headline by 1.3 pts; High; needs the capture owner, not maintenance |
| 4 | 2 | 3 | 2 | 12 | blocks the stated goal (OEE); High; needs data owners |
| 5 | 1 | 2 | 1 | 2 | informational; Medium; nothing to act on |

## Known unknowns
- OEE: run and idle time, output, good-unit and cycle-time data are missing (A10); the planned-time basis is still open (A11).
- The physical meaning of the neighbouring-position groups is a hypothesis (A13); no maintenance or contactor-change records exist to match closures to repairs.
- Rows with counts of 240-251 and a near-full list are kept and unresolved (A14).
- No screenshot spot-check has been done; the cause of the burst readings is unknown.
<!-- derived-numbers: 7.05 = 3.03+2.91+1.11 -->
