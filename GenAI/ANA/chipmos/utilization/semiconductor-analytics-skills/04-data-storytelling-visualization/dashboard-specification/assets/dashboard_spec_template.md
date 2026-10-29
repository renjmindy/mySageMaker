# Dashboard Spec - [REQUIRED: name]

**Status**: [REQUIRED]. **Dashboard owner**: [REQUIRED or OPEN]. **Data owner**: [REQUIRED or OPEN].

## Decisions it serves
1. [REQUIRED]

## Data model
Not repeated here: the single source of truth is `06-workflow-optimization/pipeline-automation/assets/timescaledb_schema.sql`. Tables: [REQUIRED - every table in the file, each in backticks].

## Panels
| id | group | type | metric | source | thresholds | notes |
|---|---|---|---|---|---|---|
| P1 | [REQUIRED: answer / diagnosis / detail / data-health / blocked] | | [metric name or -] | [table.column, ...] | [alert id or none] | |

## Queries
```sql
-- panel: P1 | columns: [REQUIRED] | rows: [minimum rows]
SELECT ...;
```

## Alerts
Rates from `scripts/alert_backtest.py` (in-sample; say so).

| id | rule | front per week | rear per week | severity | owner | action | channel |
|---|---|---|---|---|---|---|---|
| [REQUIRED] | | | | [page / ticket] | [REQUIRED or OPEN] | | |

Rejected rules: [REQUIRED - rule and its backtest rate].

## Grafana notes
[REQUIRED - limits such as the 16x16 grid]

## Refresh and retention
[REQUIRED]

## Open items
[OPTIONAL]
