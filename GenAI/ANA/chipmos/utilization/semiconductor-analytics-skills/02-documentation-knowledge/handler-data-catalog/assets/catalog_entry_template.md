# Data Catalog Entry: [REQUIRED: dataset name]

| Field | Value |
|---|---|
| Owner | [REQUIRED] |
| Source system | [REQUIRED: handler ID + screen] |
| Capture method | [REQUIRED: screenshot + OCR -> CSV] |
| Cadence | [REQUIRED: ~3-4 min] |
| Location / naming | [REQUIRED: contactor_YYYYMMDD.csv, contactor_rear_YYYYMMDD.csv] |
| History | [REQUIRED] |
| Known exclusions | [OPTIONAL: 2026-07-30 trial run] |

## Schema
| Column | Type | Description | Quality notes |
|---|---|---|---|
| Timestamp | datetime (minute) | [REQUIRED] | |
| err_01 | int | [REQUIRED] | |
| err_02 | text | [REQUIRED] | |

## Semantics and quirks
- [REQUIRED]

## Downstream consumers
- [OPTIONAL]
