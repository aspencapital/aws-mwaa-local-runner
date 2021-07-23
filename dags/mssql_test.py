import datetime as dt
import os
import re

from airflow import DAG, settings
from airflow.models import Connection
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.providers.microsoft.mssql.operators.mssql import MsSqlOperator
from airflow.utils.dates import days_ago

SM_SECRETID_NAME = "airflow/connections/mssql_qa1"
SQL_COMMAND = """SELECT TOP(9)* FROM [TDS LOANS];"""

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "concurrency": 1,
    "retries": 0,
}


def load_connection(**kwargs):
    secret_id = kwargs.get("secret_id", None)

    # set up Secrets Manager
    hook = AwsBaseHook(client_type="secretsmanager")
    client = hook.get_client_type("secretsmanager")
    connectionString = client.get_secret_value(SecretId=secret_id)["SecretString"]

    # get the conn_id
    match = re.search("([^/]+)$", secret_id)
    conn_id = match.group(1)

    # lookup current connections
    session = settings.Session()
    existing_connection = (
        session.query(Connection).filter(Connection.conn_id == conn_id).first()
    )

    # add connection if not already present
    if not existing_connection:
        print(f"adding new conn_id: {conn_id}")
        conn = Connection(conn_id=conn_id, uri=connectionString)
        session.add(conn)
        session.commit()

    return conn_id


dag = DAG(
    dag_id=os.path.basename(__file__).replace(".py", ""),
    default_args=default_args,
    description="test db connection",
    dagrun_timeout=dt.timedelta(hours=2),
    schedule_interval="@once",
)
t1 = PythonOperator(
    dag=dag,
    task_id="load_connection",
    op_kwargs={"secret_id": SM_SECRETID_NAME},
    python_callable=load_connection,
)
t2 = MsSqlOperator(
    dag=dag,
    task_id="selecting_table",
    mssql_conn_id="mssql_qa1",
    sql=SQL_COMMAND,
    database="TMO_AspenYo",
    autocommit=True,
)

t1 >> t2
