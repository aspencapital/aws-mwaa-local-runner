import datetime as dt
import logging
import os

from airflow import settings
from airflow.decorators import dag, task
from airflow.models import Connection
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.providers.microsoft.mssql.operators.mssql import MsSqlOperator
from airflow.utils.dates import days_ago

CONN_ID = "mssql_qa2"

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
        return "op_example"
    else:
        return "load_connection"


@task(do_xcom_push=False)
def load_connection(secret_id):
    print(f"adding new conn_id: {CONN_ID}")

    # set up Secrets Manager
    hook = AwsBaseHook(client_type="secretsmanager")
    client = hook.get_client_type("secretsmanager")
    connectionString = client.get_secret_value(SecretId=secret_id)["SecretString"]

    conn = Connection(conn_id=CONN_ID, uri=connectionString)
    session = settings.Session()
    session.add(conn)
    session.commit()


# https://airflow.apache.org/docs/apache-airflow-providers-microsoft-mssql/stable/_modules/airflow/providers/microsoft/mssql/hooks/mssql.html#MsSqlHook
# https://airflow.apache.org/docs/apache-airflow/1.10.12/_modules/airflow/hooks/dbapi_hook.html
@task(do_xcom_push=False)
def hook_example1(conn_id, database, query):
    # get connection
    hook = MsSqlHook(
        mssql_conn_id=conn_id,
        schema=database,
    )
    conn = hook.get_conn()

    # get cursor
    cursor = conn.cursor()
    cursor.execute(query)
    row = cursor.fetchone()

    if row:
        logging.info(row)


@task(do_xcom_push=False)
def hook_example2(conn_id, database, query):
    # get connection
    hook = MsSqlHook(
        mssql_conn_id=conn_id,
        schema=database,
    )
    row = hook.get_first(query)

    if row:
        logging.info(row)


@dag(
    # auto name the dag with filename
    dag_id=os.path.basename(__file__).replace(".py", ""),
    default_args=default_args,
    description="test db connection",
    dagrun_timeout=dt.timedelta(hours=2),
    schedule_interval="@once",
    template_searchpath="/usr/local/airflow/dags/include",
)
def generate_dag():
    # encapsulate tasks with start/end
    start = DummyOperator(task_id="start")
    end = DummyOperator(task_id="end")

    # task definitions
    _check_mssql_connection = BranchPythonOperator(
        task_id="check_mssql_connection", python_callable=check_connection
    )
    _load_connection = load_connection(f"airflow/connections/{CONN_ID}")
    _op_example = MsSqlOperator(
        task_id="op_example",
        trigger_rule="none_failed",
        mssql_conn_id=CONN_ID,
        sql="mssql_test.j2.sql",
        database="TMO_AspenYo",
        params={"count": 5},
        autocommit=True,
    )
    select_query = "SELECT TOP(5)* FROM [TDS LOANS];"
    _hook_example1 = hook_example1(
        conn_id=CONN_ID, database="TMO_AspenYo", query=select_query
    )
    _hook_example2 = hook_example2(
        conn_id=CONN_ID, database="TMO_AspenYo", query=select_query
    )

    # task relationships
    (
        start
        >> _check_mssql_connection
        >> _load_connection
        >> _op_example
        >> [_hook_example1, _hook_example2]
        >> end
    )
    _check_mssql_connection >> _op_example


dag = generate_dag()
