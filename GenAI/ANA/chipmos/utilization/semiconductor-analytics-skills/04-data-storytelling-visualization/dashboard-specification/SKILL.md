---
name: dashboard-specification
description: Specify the Grafana/web dashboard for handler utilization - panels, queries, alerts with backtested false-alarm rates, and refresh - on one schema (TimescaleDB/PostgreSQL) and check the spec by dry-running its queries. Activate when moving from one-off analysis to a live dashboard.
---

# When to use
- Turning the analysis into a continuously refreshed dashboard
- Aligning engineering and fab ops on panels, definitions, alert thresholds and owners
- Changing the data model or an alert and needing to know what it breaks

# Process
1. **List the decisions the dashboard serves** — which closed groups to inspect first (what is closed *now*), whether capacity is changing, whether the data can be trusted right now.
2. **Use the one schema** — `06-workflow-optimization/pipeline-automation/assets/timescaledb_schema.sql` is the single source of truth; never copy table definitions into the spec. Extend that file, keep its status lists equal to `lib/contactor_io.py`, and name every table in the spec's Data model section.
3. **Define panels** in a table (id, group, type, metric, `table.column` sources, thresholds, notes). Groups: answer (top row), diagnosis, detail, data-health (capture health, separate from equipment health), blocked (OEE, until run and idle time, output, good-unit and cycle-time data exist - no number shown). Every non-blocked panel has a tagged SQL query (`-- panel: Pn | columns: a, b | rows: N`).
4. **Define alerts only after backtesting them** — `scripts/alert_backtest.py` gives each rule's rate per week on the history. A rule that fires on ~40% of days (capacity below the observed average) is noise; "page" severity needs about one alert a week or less; list rejected rules with their numbers. Every alert has an owner, an action and a channel.
5. **Dry-run the spec** — `scripts/build_dashboard_db.py` builds a SQLite copy from the schema file and loads the cleaned data; `scripts/dashboard_spec_check.py` runs every query against it, checks columns and row counts, that P1/P2 equal the analysis headline, that every source column exists, that data-health panels read only capture data, that OEE panels are blocked, and that alert rates equal the backtest.
6. **Specify refresh and retention**, and the Grafana limits (no native 16x16 grid: build it from a table query or embed the generated HTML report).
7. **Review with users**, name owners, record open items in the assumptions log; run the queries on a real PostgreSQL/Timescale instance (only the SQLite dry-run exists today).

# Inputs the skill needs
- Required: metric definitions (`semiconductor-metric-definitions`) and the schema file
- Required: the cleaned data (read through `lib/contactor_io.py`)
- Optional: alert channels (Slack / LINE / email) and on-call owners; a real database to run the queries on

# Output
- `assets/dashboard_spec_template.md` (template) and `assets/dashboard_spec_sep_oct_2026.md` (filled)
- `scripts/build_dashboard_db.py` (SQLite copy loaded with the data), `scripts/alert_backtest.py` (rates per week), `scripts/dashboard_spec_check.py` (PASS/WARN/FAIL) and `scripts/test_dashboard_spec_check.py` (18 unit tests that break the real spec one way at a time)
