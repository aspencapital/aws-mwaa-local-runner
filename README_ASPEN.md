# Aspen Capital README
This README clarifies usage of `aws-mwaa-local-runner` for development purposes.

## Configuration

### Environment Variables
Add custom environment variables with a `docker/.env` file which will not be captured by git.

### Connections
Custom connections can be added to `docker/.env` using the format `AIRFLOW_CONN_{CONN_ID}`, see the [documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/connection.html#storing-a-connection-in-environment-variables). But, any connections created this way will **NOT** be visible in the airflow UI although they will still be accessible to the dags.

**NOTE**: special characters in the password or hostname must be URL encoded. The example shows a backslash encoded with `%5C` for the hostname.

```env
# connection id: mssql_qa1
AIRFLOW_CONN_MSSQL_QA1=mssql://saNodeQA:password@devserver.flanderscapital.com%5Cqa1:49637
```

## Running the Airflow CLI
You can shell into the container running `amazon/mwaa-local:2.0.2` to run airflow cli commands, but there is an extra step you must take to properly setup your environment.

I was finding that trying to run simple commands like `airflow info` were failing after shelling in. The error was showing an SQLite exception for my library files being too old. Fixing that problem is a red herring, because this configuration is using Postgres as the backing database and not the default setting for SQLite.

```bash
airflow@769bc2778687 ~]$ airflow info
Traceback (most recent call last):
  File "/usr/local/bin/airflow", line 5, in <module>
    from airflow.__main__ import main
  File "/usr/local/airflow/.local/lib/python3.7/site-packages/airflow/__init__.py", line 34, in <module>
    from airflow import settings
  File "/usr/local/airflow/.local/lib/python3.7/site-packages/airflow/settings.py", line 34, in <module>
    from airflow.configuration import AIRFLOW_HOME, WEBSERVER_CONFIG, conf  # NOQA F401
  File "/usr/local/airflow/.local/lib/python3.7/site-packages/airflow/configuration.py", line 1113, in <module>
    conf.validate()
  File "/usr/local/airflow/.local/lib/python3.7/site-packages/airflow/configuration.py", line 201, in validate
    self._validate_config_dependencies()
  File "/usr/local/airflow/.local/lib/python3.7/site-packages/airflow/configuration.py", line 242, in _validate_config_dependencies
    f"error: sqlite C library version too old (< {min_sqlite_version}). "
airflow.exceptions.AirflowConfigException: error: sqlite C library version too old (< 3.15.0). See https://airflow.apache.org/docs/apache-airflow/2.1.2/howto/set-up-database.rst#setting-up-a-sqlite-database
```

I also found that none of the exported environment variables defined in `docker/script/entrypoint.sh` were showing up. Airflow should have been recognizing that I was using Postgres instead of SQLite. This is handled by the environment variable `AIRFLOW__CORE__SQL_ALCHEMY_CONN` which did not exist. I was only seeing the environment variables which I had defined in `docker/.env`. The solution to this problem is answered [here](https://forums.docker.com/t/question-about-exporting-enviromental-variables-to-containers-using-an-entrypoint-script/105045/2).

The fix is to run the entrypoint script once you have shelled into the container, which gives you access to a new shell with the proper environmental settings.

```bash
# get id of amazon/mwaa-local container
docker ls

# shell into the container (using first few characters of container id)
docker exec -it 0000 bash

# pass shell command to the entrypoint script and create a new nested shell
/entrypoint.sh bash

# airflow commands now work
airflow info
```
