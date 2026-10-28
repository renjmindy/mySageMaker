---
name: downtime-time-series
description: Daily and hour-of-day trend of site availability with robust anomaly flags. Activate to see whether availability is improving, to find abnormal days, or to check for shift/time-of-day patterns.
---

# When to use
- Weekly/monthly availability review
- Triage of an abnormal day (is it a data artefact or a real drop?)
- Checking for hour-of-day or day-of-week effects (shift changes, lot starts)

# Process
1. **Compute the daily series** per side with `scripts/daily_trend.py` (time-weighted, cleaned). The table also shows valid samples, failure rate and coverage, and marks days with >= 5% failed readings as "bad reads?".
2. **Smooth** — 7-day rolling mean for the trend line.
3. **Flag anomalies** — robust z-score using median and MAD, threshold 2.5 (A20). The script prints the deviation in points a day needs to be flagged and the number of flags expected by chance; a 3.5 threshold cannot fire on this data. Flagged days that also have a high failure rate are listed separately - check data quality first.
4. **Cross-check flagged days** with `contactor-log-validation` (near-full reads, N/A bursts) before calling them events.
5. **Level shift and hour of day** — the script tests the best single split (permutation p-value) and each hour against the same day's mean, with standard errors and the number of hours beyond 2 SE next to ~1.1 expected by chance. It then repeats the hour test without readings of >= 60 closed sites: a pattern that vanishes is driven by large-closure bursts (capture artefact or real event?), not a steady time-of-day effect.
6. **Interpret** — separate level shifts (maintenance / fix) from spikes (noise).
7. **Fill `assets/ts_report_template.md`**.

# Inputs the skill needs
- Required: cleaned logs for >= 2 weeks
- Optional: shift schedule and maintenance calendar for annotation

# Output
- Console: daily series with data-quality columns, rolling mean and anomaly flags; level-shift test; hour-of-day effects with standard errors and a burst-robustness line
- `assets/ts_report_template.md` (filled)
