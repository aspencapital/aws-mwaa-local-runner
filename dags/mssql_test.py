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
    # set up Secrets Manager
    hook = AwsBaseHook(client_type="secretsmanager")
    client = hook.get_client_type("secretsmanager")
    response = client.get_secret_value(SecretId=SM_SECRETID_NAME)
    connectionString = response["SecretString"]

    # get the conn_id
    match = re.search("([^/]+)$", SM_SECRETID_NAME)
    conn_id = match.group(1)

    # lookup current connections
    session = settings.Session()
    connections = map(lambda x: str(x), session.query(Connection).all())

    # add connection if not already present
    if conn_id not in connections:
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
t1 = PythonOperator(dag=dag, task_id="load_connection", python_callable=load_connection)
t2 = MsSqlOperator(
    dag=dag,
    task_id="selecting_table",
    mssql_conn_id="mssql_qa1",
    sql=SQL_COMMAND,
    database="TMO_AspenYo",
    autocommit=True,
)

t1 >> t2
