# Dashboard Spec - Handler test-position capacity

**Status**: draft for review. **Dashboard owner**: [OPEN]. **Data owner**: [OPEN]. Handler id: `unspecified` (the logs carry none; catalog entry item open).

## Decisions it serves
1. **Which closed groups to inspect first** (maintenance, daily) - what is closed *now*, not the month average.
2. **Is capacity changing** (weekly review) - with the uncertainty shown.
3. **Is the data trustworthy right now** (continuous) - capture health shown separately from equipment health.

## Data model
Not repeated here. The single source of truth is `06-workflow-optimization/pipeline-automation/assets/timescaledb_schema.sql` (TimescaleDB/PostgreSQL). Tables: `contactor_samples`, `closure_episodes`, `closure_events`, `site_recency`, `equipment_daily_metrics`, `capacity_summary`. `scripts/build_dashboard_db.py` derives a SQLite copy from that file and loads the cleaned data so every query below can be dry-run (`scripts/dashboard_spec_check.py`). Status values and cleaning rules follow `lib/contactor_io.py` and `02-documentation-knowledge/semiconductor-metric-definitions/assets/metric_definition.yaml`.

## Panels
Groups: answer (top row), diagnosis (middle), detail (bottom), data-health (separate row), blocked.

| id | group | type | metric | source | thresholds | notes |
|---|---|---|---|---|---|---|
| P1 | answer | stat | site_availability | capacity_summary.availability | none | front share able to test, with P3 range under it |
| P2 | answer | stat | site_availability | capacity_summary.availability | none | rear share able to test |
| P3 | answer | stat | site_availability_low | capacity_summary.ci_low, capacity_summary.ci_high, capacity_summary.availability_low | none | plausible range and count-based lower bound, shown beside P1/P2 so both figures are visible (A21) |
| P4 | answer | stat | currently_closed_site_rate | capacity_summary.closed_now | none | positions closed >= 50% of the last 7 days |
| P5 | diagnosis | timeseries | site_availability | equipment_daily_metrics.site_availability | CAP_LOW alert | daily, both sides; range band from P3 |
| P6 | diagnosis | table (16x16 grid) | currently_closed_site_rate | site_recency.share_recent, site_recency.status | colour by share | the handler's grid; see Grafana notes |
| P7 | diagnosis | table | currently_closed_site_rate | site_recency.share_recent, site_recency.share_period, site_recency.status | none | positions closed now, ranked |
| P8 | diagnosis | bar gauge | chronic_site_rate | site_recency.share_period | none | share of closure time by position (Pareto); a history view, not an action list |
| P9 | detail | table | - | closure_events.duration_min, closure_events.n_sites, closure_events.block_aligned | GROUP_LONG alert | aligned groups closed 24 h or more |
| P10 | data-health | timeseries | - | equipment_daily_metrics.fail_pct | DQ_FAIL_DAY alert | share of readings dropped per day |
| P11 | data-health | stat | - | contactor_samples.ts | DQ_STALE alert | age of the last reading per side (now minus last_ts) |
| P12 | data-health | timeseries | - | equipment_daily_metrics.coverage_pct | none | readings per day against ~360 expected |
| P13 | blocked | text | oee | - | none | OEE: BLOCKED until run and idle time, output, good-unit and cycle-time data exist; no number is shown |

## Queries
Dry-run against the SQLite copy by `dashboard_spec_check.py`; the tag lists the columns (and a minimum row count) the panel expects. `$__timeFilter(col)` is a Grafana macro (treated as true in the dry-run).

```sql
-- panel: P1 | columns: availability | rows: 1
SELECT availability FROM capacity_summary WHERE side = 'front';
```
```sql
-- panel: P2 | columns: availability | rows: 1
SELECT availability FROM capacity_summary WHERE side = 'rear';
```
```sql
-- panel: P3 | columns: side, ci_low, ci_high, availability_low | rows: 2
SELECT side, ci_low, ci_high, availability_low FROM capacity_summary ORDER BY side;
```
```sql
-- panel: P4 | columns: side, closed_now | rows: 2
SELECT side, closed_now FROM capacity_summary ORDER BY side;
```
```sql
-- panel: P5 | columns: day, side, site_availability | rows: 60
SELECT day, side, site_availability FROM equipment_daily_metrics WHERE $__timeFilter(day) ORDER BY day;
```
```sql
-- panel: P6 | columns: grid_row, grid_col, share_recent, status | rows: 256
SELECT ((site - 1) / 16) + 1 AS grid_row, ((site - 1) % 16) + 1 AS grid_col, share_recent, status
FROM site_recency WHERE side = 'front';
```
```sql
-- panel: P7 | columns: side, site, share_recent, share_period, status | rows: 1
SELECT side, site, share_recent, share_period, status FROM site_recency
WHERE share_recent >= 0.5 ORDER BY share_recent DESC, share_period DESC;
```
```sql
-- panel: P8 | columns: site, share_period, cumulative_share | rows: 256
SELECT site, share_period,
       SUM(share_period) OVER (ORDER BY share_period DESC, site) * 1.0 / (SELECT SUM(share_period) FROM site_recency WHERE side = 'front') AS cumulative_share
FROM site_recency WHERE side = 'front' ORDER BY share_period DESC, site;
```
```sql
-- panel: P9 | columns: event_id, side, start_ts, end_ts, duration_min, n_sites, block_aligned | rows: 1
SELECT event_id, side, start_ts, end_ts, duration_min, n_sites, block_aligned FROM closure_events
WHERE n_sites >= 4 AND block_aligned >= 0.9 AND duration_min >= 1440 ORDER BY duration_min DESC LIMIT 20;
```
```sql
-- panel: P10 | columns: day, side, fail_pct | rows: 60
SELECT day, side, fail_pct FROM equipment_daily_metrics WHERE $__timeFilter(day) ORDER BY day;
```
```sql
-- panel: P11 | columns: side, last_ts | rows: 2
SELECT side, MAX(ts) AS last_ts FROM contactor_samples GROUP BY side;
```
```sql
-- panel: P12 | columns: day, side, coverage_pct | rows: 60
SELECT day, side, coverage_pct FROM equipment_daily_metrics WHERE $__timeFilter(day) ORDER BY day;
```

## Alerts
Rates are **backtested** on the 51 days of history (`scripts/alert_backtest.py`; in-sample, about 7.3 weeks - orders of magnitude, not guarantees). Severity "page" is only for rules under about one alert a week per side.

| id | rule | front per week | rear per week | severity | owner | action | channel |
|---|---|---|---|---|---|---|---|
| CAP_LOW | daily capacity below (median - 2 SD) of the previous 28 days; Grafana alert on P5 | 0.38 | 0.38 | ticket | [OPEN] | check P6/P7 and the data-health row before acting | [OPEN] |
| GROUP_LONG | an aligned group (4+ positions) has been closed 72 hours; query `alert: GROUP_LONG` | 1.65 | 0.96 | ticket | [OPEN] | inspect the group (cause is a hypothesis) | [OPEN] |
| DQ_FAIL_DAY | 10% or more of a day's readings dropped; query `alert: DQ_FAIL_DAY` | 0.27 | 0.14 | ticket | [OPEN] | ask the capture owner; treat capacity numbers for that day with caution | [OPEN] |
| DQ_STALE | no reading for more than 30 minutes (now minus P11); Grafana alert on P11 | 0.14 | 0.27 | page | [OPEN] | check the capture pipeline | [OPEN] |

```sql
-- alert: GROUP_LONG | columns: side, event_id, duration_min | rows: 0
SELECT side, event_id, duration_min FROM closure_events
WHERE n_sites >= 4 AND block_aligned >= 0.9 AND duration_min >= 4320 AND ongoing = 1;
```
```sql
-- alert: DQ_FAIL_DAY | columns: side, day, fail_pct | rows: 0
SELECT side, day, fail_pct FROM equipment_daily_metrics WHERE fail_pct >= 10;
```

Rejected rules (kept for the reasoning): *capacity below the observed average* (front 91%, rear 96%) would alert on 23 of 51 front days (3.16 per week) and 23 of 51 rear days (3.16 per week), about 45% of days; *any aligned group closing for 30 minutes or more* would alert 13.04 per week on the front and 9.47 on the rear. CAP_LOW fired on 2 front days and 2 rear days in the backtest (0.38 per week each); it needs a drop of roughly 4-6 points, so it is a safety net, and GROUP_LONG plus the data-health alerts carry the actionable load. No alert watches the count-versus-list gap of open question A21; the dashboard shows the count-based lower bound beside the headline instead (P3).

## Grafana notes
- Grafana has no built-in 16x16 cell grid. P6 is built from the query above as a table or a plugin visual, one cell per position coloured by `share_recent`; the plugin choice is [OPEN]. The generated HTML report (`visualization-builder`) is the reference design and can be embedded in the meantime.
- P3 sits beside P1/P2 so a single exact figure is never shown alone; P8 is a history view and the dashboard must not present it as the maintenance list (P7 is).
- Every number links to its definition (metric definitions file) and shows the cleaning rules on hover.
- Debounce: alerts evaluate on the debounced closure episodes, never on a single reading.

## Refresh and retention
- Readings arrive about every 4 minutes; the pipeline loads them hourly and closes the day shortly after midnight (`pipeline-automation`, Airflow or cron). Dashboard auto-refresh every 5 minutes. Capture-to-database latency: [OPEN].
- Retention of raw readings: [OPEN - data owner to decide]; daily and summary tables are small and kept indefinitely.

## Open items
- Owners for the dashboard, data and each alert; alert channels (Slack, LINE or email).
- A19 (7-day recency window and status thresholds) is applied but unconfirmed; the status words on P6/P7 depend on it.
- A21 (open): since 2026-10-05 the count exceeds the listed sites by about 40; P1/P2 show the list-based figure and P3 the count-based lower bound until it is answered.
- OEE panels stay blocked (A10, A11).
- Run the queries on a real PostgreSQL/Timescale instance loaded by the pipeline: only the SQLite dry-run exists.
