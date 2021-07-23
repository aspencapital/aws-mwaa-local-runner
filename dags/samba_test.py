import datetime as dt

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.samba.hooks.samba import SambaHook

FILEPATH = ""
SAMBA_CONN_ID = "samba_qa"

default_args = {
    "owner": "airflow",
    "start_date": dt.datetime(2021, 1, 1, 00, 00, 00),
    "concurrency": 1,
    "retries": 0,
}

dag = DAG(
    "samba_test",
    default_args=default_args,
    description="test samba connection",
    schedule_interval="@once",
)


def list_directory(**kwargs):
    path = kwargs.get("path", None)
    samba_conn_id = kwargs.get("samba_conn_id", None)
    samba_hook = SambaHook(samba_conn_id=samba_conn_id)
    samba_client = samba_hook.get_conn()
    samba_files = samba_client.listdir(path)
    print(samba_files)


with DAG(
    "samba_test",
    default_args=default_args,
    description="test samba connection",
    schedule_interval="@once",
) as dag:
    start = DummyOperator(task_id="start")
    bash = BashOperator(task_id="bash_1", bash_command='echo "HELLO!"')
    python = PythonOperator(
        task_id="python_1",
        # python_callable=lambda: print("GOODBYE!"))
        op_kwargs={"path": FILEPATH, "samba_conn_id": SAMBA_CONN_ID},
        python_callable=list_directory,
    )
    end = DummyOperator(task_id="end")

start >> bash, python >> end
