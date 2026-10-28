"""Example Airflow DAG (template - not executed by this repo; requires apache-airflow)."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="handler_utilization_daily",
    start_date=datetime(2026, 10, 1),
    schedule="10 0 * * *",          # daily close shortly after midnight
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=10)},
) as dag:
    run = BashOperator(
        task_id="run_pipeline",
        bash_command="python -I /opt/semiconductor-analytics-skills/06-workflow-optimization/"
                     "pipeline-automation/scripts/daily_pipeline.py",
    )
