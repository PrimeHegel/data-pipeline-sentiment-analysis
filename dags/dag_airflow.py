from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "hegel",
    "start_date": datetime(2026, 4, 20),
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

dag = DAG(
    "sentiment_analysis_express",
    default_args=default_args,
    description="ETL pipeline: Kaggle CSV → data_raw → data_cleansed → sentiment_results",
    schedule_interval="*/2 * * * *",
    catchup=False,
    max_active_runs=1,
)

t1 = BashOperator(task_id="extract_to_raw_db", bash_command="cd /opt/airflow && python3 src/extract.py", dag=dag)
t2 = BashOperator(task_id="transform_to_cleansed_db", bash_command="cd /opt/airflow && python3 src/transform.py", dag=dag)
t3 = BashOperator(task_id="naive_bayes_modelling", bash_command="cd /opt/airflow && python3 src/modelling.py", dag=dag)

t1 >> t2 >> t3