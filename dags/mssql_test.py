import datetime as dt
import time

from airflow import DAG
from airflow.providers.microsoft.mssql.operators.mssql import MsSqlOperator

default_args = {
    'owner': 'airflow',
    'start_date': dt.datetime(2019, 11, 8, 23, 00, 00),
    'concurrency': 1,
    'retries': 0
}

dag = DAG(
    'mssql_test',
    default_args=default_args,
    description='test db connection',
    schedule_interval='@once'
)

sql_command = """SELECT TOP(10)* FROM [TDS LOANS];"""
t1 = MsSqlOperator( task_id = 'selecting_table',
                    mssql_conn_id = 'mssql_qa1',
                    sql = sql_command,
                    dag = dag,
                    database = 'TMO_AspenYo',
                    autocommit = True)

t1
