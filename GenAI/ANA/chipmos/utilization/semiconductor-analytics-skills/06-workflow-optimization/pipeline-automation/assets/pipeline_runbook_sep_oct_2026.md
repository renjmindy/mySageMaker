# Pipeline Runbook - handler contactor utilization (handler id: unspecified)

Schedule: not set [OPEN]   Owner: not named [OPEN]   Alert channel: not chosen [OPEN]   Staleness limit (--max-data-age-hours): not set [OPEN - the data owner decides; the option has no default]
The Airflow example suggests a daily run shortly after midnight; nothing is scheduled today, so the pipeline runs only when someone starts it.

## What a run does
Run `python 06-workflow-optimization/pipeline-automation/scripts/daily_pipeline.py`. Steps, in order, each logged to `out/pipeline/<run>/<step>.log`: validation, availability, chronic_front, chronic_rear, events_front, events_rear, dashboard_db (the SQLite copy of the dashboard tables), store (CSV files and `load.sql` for PostgreSQL), alerts (the dashboard spec's alert rules, evaluated), heatmap, qa (the QA gate: `--gate full` runs the whole repository gate, `--gate data` only the data gate). Then the headline and the age of the newest reading are recomputed, and the summary is written.

## Reading the result
- Exit code: 0 ok, 1 failed or crashed, 2 another run is active.
- `status` in `summary.json`: ok (every step ok), failed (a step failed, or the freshness limit was exceeded), crashed (something raised; the summary and `error` are still written).
- `out/pipeline/latest.json` points at the newest ok run; a failed run never replaces it, and `published` in the summary says whether this run was.
- The summary also holds the commit, durations per step, the data's last reading and age, the QA counts, the alerts firing and what the notification hook did.

## Failure modes and response
| mode | how it shows | response |
|---|---|---|
| capture stopped (no new readings) | `data.age_hours` grows; with a limit set, `freshness` fails the run; DQ_STALE fires | ask the capture owner; do not publish numbers for the missing days |
| a step failed | `status: failed`, the step shows `FAILED(n)` | read `<step>.log`; fix, then rerun; the run is not published |
| QA gate FAIL | the `qa` step fails; `qa.log` lists the failing checks | fix the cause (a stale generated block fails a data run only with `--gate full`); waivers never cover a FAIL |
| crash (the loader raised, bad file) | `status: crashed` with `error` | fix the data format; the logs of the steps that ran are kept |
| another run active | exit code 2, no run folder | wait; a lock left by a dead process is removed automatically |
| alerts firing | `alerts_firing` lists them; the hook is called with `alerts` | act per the dashboard spec; owners and channel are open items |
| notification hook failing | `notified` shows `hook exited n` or `hook failed` | the run result is unaffected; fix the hook |

## Backfill, retention, what is not built
- Backfill or a staging copy: `--data-dir` and `--start`.
- Retention: `--keep N` removes older run folders after an ok run; nothing is removed by default.
- Not built: loading PostgreSQL/Timescale (the `store` step only exports CSV files and `load.sql`; it is an initial load into an empty schema, the key policy for incremental loads is the data owner's decision, and it has not been run against a database); delivering alerts (no channel or owner chosen); running Airflow or cron for real (the DAG example is a template that has not been executed).
