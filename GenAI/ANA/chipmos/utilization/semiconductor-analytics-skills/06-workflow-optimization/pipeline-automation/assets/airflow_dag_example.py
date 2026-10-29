"""Example Airflow DAG (template - not executed by this repo; requires apache-airflow).

Differences from a bare schedule: one active run at a time (the pipeline also holds a lock), a timeout, and a
failure callback that calls the same hook the pipeline uses (PIPELINE_NOTIFY_CMD, read from the environment: no
channel or credential is stored in this file). The pipeline's exit code is the task's result: 0 ok, 1 failed or
crashed, 2 another run is active.
"""
import os
import shlex
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


def notify_failure(context):
    """Airflow-level failures (a timeout, a crash before the pipeline started) that the pipeline cannot report itself."""
    cmd = os.environ.get("PIPELINE_NOTIFY_CMD")
    if cmd:
        subprocess.run(shlex.split(cmd) + ["airflow-failed", str(context.get("run_id", ""))], timeout=60, check=False)


with DAG(
    dag_id="handler_utilization_daily",
    start_date=datetime(2026, 10, 1),
    schedule="10 0 * * *",          # daily close shortly after midnight
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=1),
    default_args={"retries": 1, "retry_delay": timedelta(minutes=10), "on_failure_callback": notify_failure},
) as dag:
    run = BashOperator(
        task_id="run_pipeline",
        # add --max-data-age-hours N once the data owner has set the limit (it has no default on purpose)
        bash_command="python -I /opt/semiconductor-analytics-skills/06-workflow-optimization/"
                     "pipeline-automation/scripts/daily_pipeline.py --keep 30",
    )
