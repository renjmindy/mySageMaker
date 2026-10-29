---
name: pipeline-automation
description: Run the utilization workflow end to end as a monitored job - clean, compute, gate, build the dashboard database, export it for PostgreSQL, evaluate the alert rules - with honest failure semantics (any failed step fails the run), an always-written summary, a lock, retention, a data-age limit and a notification hook. Activate when the manual analysis should become a scheduled job, or to understand what the daily run does and does not do.
---

# When to use
- Moving from ad-hoc scripts to a daily/hourly job
- Standing up the storage tables, the scheduler and the alert path
- Checking what a run proves, and what it does not

# Process
1. **Ingest** — new CSVs land in the data folder (screen capture today; direct handler logs later). The pipeline does not fetch them: it reads the folder and reports the age of the newest reading, and with `--max-data-age-hours N` fails the run when a side is older. The limit has no default: the data owner sets it.
2. **Clean, compute, gate** — `scripts/daily_pipeline.py` runs, in order: validation, availability, chronic sites (front, rear), events (front, rear), the dashboard database, the PostgreSQL export, the alert evaluation, the heatmap and the QA gate (`--gate full` = the whole repository gate, `--gate data` = the data gate only; use `data` for a daily job so a stale document cannot fail a data refresh).
3. **Judge the run** — a run is `ok` only if every step is ok; a failed step, a failed gate or an exceeded freshness limit makes it `failed`; an exception makes it `crashed`. The summary (`out/pipeline/<run>/summary.json`) is always written, and `out/pipeline/latest.json` moves only to a run that is ok.
4. **Store** — the `store` step exports one CSV per dashboard table and a `load.sql` (`scripts/export_for_postgres.py`). It is an initial load into an empty schema (`assets/timescaledb_schema.sql`); no connection code exists, it has not been run against a database, and the key policy for incremental loads is the data owner's decision.
5. **Alert** — `scripts/evaluate_alerts.py` evaluates the dashboard spec's rules (GROUP_LONG, DQ_FAIL_DAY, CAP_LOW, DQ_STALE); `PIPELINE_NOTIFY_CMD` (environment, never stored in the repo) is called with `failed` or `alerts` and the summary path. No channel or owner is chosen yet.
6. **Schedule** — cron or the Airflow template (`assets/airflow_dag_example.py`: one active run, a timeout, a failure callback). The template has not been executed. One run at a time is enforced by a lock; a second run exits with code 2.
7. **Operate** — `assets/pipeline_runbook_sep_oct_2026.md` (failure modes and responses, backfill with `--data-dir` and `--start`, retention with `--keep N`, what is not built).

# Inputs the skill needs
- Required: data folder or feed, scheduler access, a data owner who sets the staleness limit
- Optional: DB connection details (never stored in the repo), alert channels and owners, a notification command

# Output
- `out/pipeline/<run>/` logs, `summary.json`, `alerts.json`, `postgres/` (CSV files and `load.sql`); `out/pipeline/latest.json`
- `assets/timescaledb_schema.sql`, `assets/airflow_dag_example.py`, `assets/pipeline_runbook_sep_oct_2026.md` (and its template)
- `scripts/daily_pipeline.py`, `scripts/evaluate_alerts.py`, `scripts/export_for_postgres.py` and `scripts/test_pipeline.py` (fake-step tests: failed step, crash, lock, retention, freshness, notification, alert rules, export round trip)
