import datetime as dt
import os

from airflow import DAG, settings
from airflow.models import Connection
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.providers.microsoft.mssql.operators.mssql import MsSqlOperator
from airflow.utils.dates import days_ago

CONN_ID = "mssql_qa2"
SQL_COMMAND = """SELECT TOP(9)* FROM [TDS LOANS];"""

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "concurrency": 1,
    "retries": 0,
}


def check_connection(**kwargs):
    session = settings.Session()
    connection = session.query(Connection).filter(Connection.conn_id == CONN_ID).first()
    if connection:
        return "query_table"
    else:
        return "load_connection"


def load_connection(**kwargs):
    secret_id = kwargs.get("secret_id", None)

    print(f"adding new conn_id: {CONN_ID}")

    # set up Secrets Manager
    hook = AwsBaseHook(client_type="secretsmanager")
    client = hook.get_client_type("secretsmanager")
    connectionString = client.get_secret_value(SecretId=secret_id)["SecretString"]

    conn = Connection(conn_id=CONN_ID, uri=connectionString)
    session = settings.Session()
    session.add(conn)
    session.commit()


dag = DAG(
    dag_id=os.path.basename(__file__).replace(".py", ""),
    default_args=default_args,
    description="test db connection",
    dagrun_timeout=dt.timedelta(hours=2),
    schedule_interval="@once",
)
start = DummyOperator(dag=dag, task_id="start")
end = DummyOperator(dag=dag, task_id="end")
check = BranchPythonOperator(
    dag=dag, task_id="check_mssql_connection", python_callable=check_connection
)
load = PythonOperator(
    dag=dag,
    task_id="load_connection",
    op_kwargs={"secret_id": f"airflow/connections/{CONN_ID}"},
    python_callable=load_connection,
    do_xcom_push=False,
)
query = MsSqlOperator(
    dag=dag,
    task_id="query_table",
    trigger_rule="none_failed",
    mssql_conn_id=CONN_ID,
    sql=SQL_COMMAND,
    database="TMO_AspenYo",
    autocommit=True,
)

start >> check >> load >> query
check >> query
query >> end
