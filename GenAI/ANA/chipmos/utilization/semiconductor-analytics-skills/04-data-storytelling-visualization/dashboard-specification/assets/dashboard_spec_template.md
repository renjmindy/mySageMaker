# Dashboard Spec - [REQUIRED: name]

## Data model
```sql
-- raw, one row per capture and side
contactor_samples(ts timestamptz, handler text, side text, err_01 int, closed_sites int[], status text, weight_min real)
-- derived
site_state_events(ts timestamptz, handler text, side text, site int, event text, event_id bigint)
equipment_daily_metrics(day date, handler text, side text, site_availability real, availability_low real, valid_samples int)
```

## Panels
| Panel | Type | Query / source | Thresholds |
|---|---|---|---|
| [REQUIRED] | | | |

## Alerts
| Alert | Condition | Channel | Owner |
|---|---|---|---|
| [REQUIRED] | | | |

## Refresh and retention
[REQUIRED]
