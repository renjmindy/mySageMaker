# Pipeline Architecture (from project docs, adapted)

| Layer | Docs say | This project today |
|---|---|---|
| 1 Ingestion | PLC/SCADA/MES via Modbus, OPC UA, MQTT; error codes err_01/err_02 | screen capture -> OCR -> CSV (`err_01` count, `err_02` list) |
| 2 ETL | de-glitch, align to shifts | loader rules + time weights; shift slicing later |
| 3 Calculation | A, P, Q, OEE | site availability only |
| 4 Storage / scheduling | TimescaleDB/InfluxDB; Airflow or cron | `assets/timescaledb_schema.sql`; `daily_pipeline.py` |
| 5 Dashboard / alerts | Grafana; Slack/LINE/Email at < 75% | spec in `dashboard-specification` |

Docs' alert example (OEE < 75%) is an OEE threshold - for site availability set thresholds from the observed baseline.
Preferred future ingestion: replace OCR with direct handler logs - removes the 252-256 and garbled-ID problems.
