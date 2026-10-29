# Pipeline Architecture (from project docs, adapted)

| Layer | Docs say | This project today |
|---|---|---|
| 1 Ingestion | PLC/SCADA/MES via Modbus, OPC UA, MQTT; error codes err_01/err_02 | screen capture -> OCR -> CSV (`err_01` count, `err_02` list); the pipeline does not fetch files, it reads the data folder and reports the age of the newest reading |
| 2 ETL | de-glitch, align to shifts | loader rules + time weights; shift slicing later |
| 3 Calculation | A, P, Q, OEE | site availability only |
| 4 Storage / scheduling | TimescaleDB/InfluxDB; Airflow or cron | `assets/timescaledb_schema.sql`; the pipeline builds a SQLite copy and exports CSV files plus `load.sql` for an initial PostgreSQL load (not run against a database); `daily_pipeline.py`; an Airflow template that has not been executed |
| 5 Dashboard / alerts | Grafana; Slack/LINE/Email at < 75% | spec in `dashboard-specification`; the pipeline evaluates its alert rules and calls a notification hook if one is configured; no channel or owner chosen |

Docs' alert example (OEE < 75%) is an OEE threshold - for site availability set thresholds from the observed baseline.
Preferred future ingestion: replace OCR with direct handler logs - removes the 252-256 and garbled-ID problems.

## Run semantics
A run is ok only if every step is ok. The summary is always written, even after a crash. `latest.json` is replaced only by an ok run. One run at a time (a lock file). Exit codes: 0 ok, 1 failed or crashed, 2 locked.
