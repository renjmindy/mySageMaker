---
name: pipeline-automation
description: Automate the utilization workflow end to end - ingest, validate, compute, store, visualise, alert - following the architecture in the project docs (TimescaleDB/InfluxDB, Airflow or cron, Grafana, Slack/LINE/Email). Activate when the manual analysis should become a scheduled, monitored job.
---

# When to use
- Moving from ad-hoc scripts to a daily/hourly job
- Standing up the storage tables and DAG
- Adding data-quality and alert steps

# Process
1. **Ingest** — new CSVs (or direct captures) land in the data folder; later replace screen capture with handler logs (Modbus / OPC UA / MQTT per docs) if available.
2. **Clean and align** — `lib/contactor_io.py` applies the rules; time weights replace shift slicing for now.
3. **Compute** — availability, chronic sites, events (scripts in `03-data-analysis-investigation`).
4. **Gate** — `analysis-qa-checklist/scripts/qa_runner.py`; a FAIL stops publication.
5. **Store** — write to TimescaleDB using `assets/timescaledb_schema.sql` (raw `contactor_samples`, `site_state_events`, `equipment_daily_metrics`).
6. **Schedule** — run `scripts/daily_pipeline.py` from cron or Airflow (`assets/airflow_dag_example.py`); hourly aggregation and daily close.
7. **Alert** — thresholds from `dashboard-specification`; notify via Slack / LINE / email; alert on data staleness too.

# Inputs the skill needs
- Required: data folder or feed, DB connection details (not stored in the repo), scheduler access
- Optional: alert channels and owners

# Output
- `out/pipeline/<run>/` logs and `summary.json` from `scripts/daily_pipeline.py`
- `assets/timescaledb_schema.sql`, `assets/airflow_dag_example.py` (templates)
