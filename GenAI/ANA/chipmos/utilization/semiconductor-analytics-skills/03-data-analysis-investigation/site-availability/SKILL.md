---
name: site-availability
description: Compute time-weighted contactor-site availability per side and day from cleaned handler logs, with a lower/upper range and sensitivity to read-failure rules. Activate for any "how utilised/available are the sites" question or to produce the headline number for a period.
---

# When to use
- Producing the headline availability for front and rear over a period
- Comparing days or sides
- Showing how much a data-rule choice (e.g. near-full exclusion) moves the number

# Process
1. **Validate first** — run `contactor-log-validation`; resolve or record flagged days in the assumptions log.
2. **Load cleaned data** through `lib/contactor_io.py` (valid rows: `OK`, `NA_ZERO`).
3. **Weight by time** — each valid reading counts for the time until the next reading in the file, capped at 15 min; a dropped reading's own time is not counted, and across a capture gap the last valid reading is carried forward for at most 15 min (A18). Uneven sampling does not bias the mean; weighting differs from the plain mean by about 0.65 pt on the front.
4. **Compute availability** — `scripts/site_availability.py`: `1 - sum(closed x minutes) / (256 x sum(minutes))` per side and per day.
5. **Report a range** — list-length-based value is the optimistic bound (list under-reports closures); a count-based value (`max(err_01, list)`) is the pessimistic bound.
6. **Run the sensitivity** — repeat with `--near-full-min 0` (old 256-only rule) to show what the confirmed 252-255 rule (A8) changes.
7. **Quote the precision** — the script prints a 95% day-level bootstrap interval (about +/-0.75 pt); differences below about 1.5 pts between periods are not distinguishable from daily variation.
8. **Fill `assets/availability_report_template.md`**.

# Inputs the skill needs
- Required: cleaned contactor logs, both sides
- Required: period (default 2026-09-01 onward)
- Optional: planned-production calendar (otherwise 24x7 is assumed - assumption A11)

# Output
- Console tables: per-day and overall availability per side with range and 95% interval
- Optional CSV via `--output`
- `assets/availability_report_template.md` (filled)
