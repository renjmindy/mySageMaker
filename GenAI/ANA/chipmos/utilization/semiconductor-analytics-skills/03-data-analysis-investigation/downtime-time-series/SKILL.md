---
name: downtime-time-series
description: Daily and hour-of-day trend of site availability with robust anomaly flags. Activate to see whether availability is improving, to find abnormal days, or to check for shift/time-of-day patterns.
---

# When to use
- Weekly/monthly availability review
- Triage of an abnormal day (is it a data artefact or a real drop?)
- Checking for hour-of-day or day-of-week effects (shift changes, lot starts)

# Process
1. **Compute the daily series** per side with `scripts/daily_trend.py` (time-weighted, cleaned).
2. **Smooth** — 7-day rolling mean for the trend line.
3. **Flag anomalies** — robust z-score using median and MAD (threshold 3.5, `references/ts_patterns_guide.md`).
4. **Cross-check flagged days** with `contactor-log-validation` (near-full reads, N/A bursts) before calling them events.
5. **Hour-of-day profile** — mean closed count by hour; look for stable shift effects (small in the Sep-Oct data).
6. **Interpret** — separate level shifts (maintenance / fix) from spikes (noise).
7. **Fill `assets/ts_report_template.md`**.

# Inputs the skill needs
- Required: cleaned logs for >= 2 weeks
- Optional: shift schedule and maintenance calendar for annotation

# Output
- Console: daily series with rolling mean and anomaly flags; hour-of-day profile
- `assets/ts_report_template.md` (filled)
