# Aspen Capital README
This README clarifies usage of `aws-mwaa-local-runner` for development purposes.

## Configuration

## Python Virtual Environment
Ananconda is used to control the python environment. This expects conda to be installed on your Mac.

The followind setup should occur in a terminal outside of VSCode:

```bash
brew install --cask anaconda

# there was a permissions issue with ~/.conda directory after installation
# the directory was owned by root which causes other problems
# if this happens use the following to fix
sudo chown -R $USER:staff ~/.conda

# identify the shell you are using
conda init zsh
# relaunch terminal

# create a virtual environment for mwaa development
conda create -n mwaa python=3.7
condo info --envs

# install dependencies in conda:mwaa
pip install -r docker/config/requirements.txt -c docker/config/constraints.txt
pip install -r dags/requirements.txt

# install dependencies for MsSqlOperator
brew install postgresql
brew install unixodbc
```

To use the virtual environment in VSCode integrated terminal without having to manually switch, you will need to set `terminal.integrated.inheritEnv` to `false`. See [Integrated Terminal](https://code.visualstudio.com/updates/v1_36#_launch-terminals-with-clean-environments) in the linked Release Notes.

The correct interpreter will be chosen via the `python.pythonPath` setting in `.vscode/settings.json` file.

Linting tools must be installed with `tools/requirements.txt` to enable autoformatting capabilities. `.vscode.settings` configures Python linting and expects the requirements dependencies to be present.

```bash
pip install -r tools/requirements.txt
```

### Environment Variables
Add custom environment variables with a `docker/.env` file which will not be captured by git.

### Connections
Custom connections can be added to `docker/.env` using the format `AIRFLOW_CONN_{CONN_ID}`, see the [documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/connection.html#storing-a-connection-in-environment-variables). But, any connections created this way will **NOT** be visible in the airflow UI although they will still be accessible to the dags.

**NOTE**: special characters in the password or hostname must be URL encoded. The example shows a backslash encoded with `%5C` for the hostname.

```env
# connection id: mssql_qa1
AIRFLOW_CONN_MSSQL_QA1=mssql://saNodeQA:password@devserver.flanderscapital.com%5Cqa1:49637
```

A quick way to figure out the `.env` value for a connection is to take a peak at the values already loaded into airflow with the following commands:

```bash
airflow connections export conn.env --format env
less conn.env
```

### VSCode

#### VSCode Syntax Highlighting for Jinja SQL Files
To get jinja and SQL syntax highlighting, install the **Better Jinja** extension (`samuelcolvin.jinjahtml`). In order for airflow to properly load SQL files, the filename extension must be `*.sql` which does not work with the extension (extension expects `*.sql.j2`). A custom `file.associations` setting has been made to properly handle files with extension `*.j2.sql` to make the extension work and keep airflow happy.

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

## Samba
Found out the MWAA does not currently support the `smbclient` command, see [Samba hook and smbclient](https://forums.aws.amazon.com/thread.jspa?threadID=336238). There is a test dag for samba, but it will not work. You will get an error similar to the following:

```
FileNotFoundError: [Errno 2] No such file or directory: b'smbclient': b'smbclient'
```

Example Connection .env value
```ini
AIRFLOW_CONN_SAMBA_QA=samba://saNodeQA:password@cottonwood.flanderscapital.com/aUsers-QA%2FShared%2FLoan%20Documents%20-%20Active
```

## requirements.txt
Use the `test-requirements` subcommand to validate your dependencies before uploading to MWAA.

```bash
./mwaa-local-env test-requirements
```

Your requirements should come from the [Reference for package extras](http://airflow.apache.org/docs/apache-airflow/2.0.2/extra-packages-ref.html) as described in the AWS documentation for [Installing Python dependencies | Step two: Create the requirements.txt | 2. Review the Airflow package extras](https://docs.aws.amazon.com/mwaa/latest/userguide/working-dags-dependencies.html). Trying to install dependencies directly (e.g. `apache-airflow-providers-microsoft-mssql==2.0.0`) will work locally but fail with MWAA.

```ini
# requirements.txt
--constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.0.2/constraints-3.7.txt"

apache-airflow[microsoft.mssql,odbc,samba]==2.0.2
PySmbClient==0.1.5
```

## Connecting to AWS with SAML
The easiest way to establish a connection is to use the `aws_default` connection. You must use your temporary saml credentials after calling `saml2aws login`. You will pull the necessary values from `~/.aws/credentials` under the profile name corresponding to your saml session. In my case, I have named that profile `saml`. You can use `tools/mwaa_connection.py` to build the connection string and copy the result to the clipboard.

Example of credentials after authenticating with `saml2aws login`.
```ini
# ~/.aws/credentials
[saml]
aws_access_key_id        = ASIAZW65Y6SIEXW2J7NX
aws_secret_access_key    = 3APVbQRrUwsxImuHoXOVaJjIIcc0VZ35IgsmNGnT
aws_session_token        = FwoGZXIvYXdzEAgaDEmsIvuXH0YMOZWsOSKxAo9X/XnC2lKqcDPgVCSQOI9KC6PiPMxXfrsIMkCHtKlQZZk6Z1MHbxr3alkjs05ZHUEK/7Ia5IonypTIwiOnU/7xJBj4ctHcaePTKBZ5pKx8MKLvsJNXY9xqiWbQzkj1oXQYF2cVjas8QaBwAjLNI0LHufkGBS8EebQ4F2WMCB9GtDoPgZ4BKRME4Fni3TAuflBoA0gtKYR5iSMHdBBb1jiB2HJYlD+c+Sgp88We+qCZV6FV/lXWX0JISAwIVILEzGnSIdq9PZ9w41Mj6XMlmC9LzNULIcOVfwUsi6nAJKoXo89l1VjIsphrtZpBU8HiChLXwLowCzFlnLn+4h76+nH/6HrjUYtsvKpYihU1tGaod1HeZ/02wdh4XGjpUyVAU31hTRMym0TBwtDDMo+PRKfLKOGm64cGMipxx6Q8IMTKMI24idcs3WVz5U9BtGEkn8uucOML1/3XD2FPqgjFOUYGcAE=
```

Update the `docker/.env` file with `AIRFLOW_CONN_AWS_DEFAULT` to use the temporary credentials. Additional steps are required
* URL encode `aws_secret_access_key` for password value
* URL encode `aws_session_token`
* set `region_name`
* URL encode `role_arn`

```ini
AIRFLOW_CONN_AWS_DEFAULT=aws://ASIAZW65Y6SIEXW2J7NX:3APVbQRrUwsxImuHoXOVaJjIIcc0VZ35IgsmNGnT@?region_name=us-west-2&role_arn=arn:aws:iam::499849230022:role%2FOrganizationAccountAccessRole&aws_session_token=FwoGZXIvYXdzEAgaDEmsIvuXH0YMOZWsOSKxAo9X%2FXnC2lKqcDPgVCSQOI9KC6PiPMxXfrsIMkCHtKlQZZk6Z1MHbxr3alkjs05ZHUEK%2F7Ia5IonypTIwiOnU%2F7xJBj4ctHcaePTKBZ5pKx8MKLvsJNXY9xqiWbQzkj1oXQYF2cVjas8QaBwAjLNI0LHufkGBS8EebQ4F2WMCB9GtDoPgZ4BKRME4Fni3TAuflBoA0gtKYR5iSMHdBBb1jiB2HJYlD%2Bc%2BSgp88We%2BqCZV6FV%2FlXWX0JISAwIVILEzGnSIdq9PZ9w41Mj6XMlmC9LzNULIcOVfwUsi6nAJKoXo89l1VjIsphrtZpBU8HiChLXwLowCzFlnLn%2B4h76%2BnH%2F6HrjUYtsvKpYihU1tGaod1HeZ%2F02wdh4XGjpUyVAU31hTRMym0TBwtDDMo%2BPRKfLKOGm64cGMipxx6Q8IMTKMI24idcs3WVz5U9BtGEkn8uucOML1%2F3XD2FPqgjFOUYGcAE%3D
```

```bash
# copy session token to clipboard
grep aws_session_token ~/.aws/credentials | awk '{print $3}' | pbcopy

# you can url encode and build the environment variable manually
# OR
# use mwaa_connection.py to build connection string and copy to clipboard

# reference your ~/.aws/credentials for values
./tools/mwaa_connection.py --profile saml --clipboard \
  -x role_arn=arn:aws:iam::499849230022:role/OrganizationAccountAccessRole

# manually insert values
./tools/mwaa_connection.py \
  -l ASIAZW65Y6SIACFBUPVE \
  -p Air2oG9L3cIT0ioO0OBtehvn6nYfR2r1FQgM3YEy \
  -x region_name=us-west-2 \
  role_arn=arn:aws:iam::499849230022:role/OrganizationAccountAccessRole \
  aws_session_token=FwoGZXIvYXdzEAkaDNzgCTh36vwG/QdUyiKxAvmtOMrF6suFOmnp4CxoNKXPX7JzBaC+KWn8DymCTTylpdndri6QL11O4bqi0xldbn9k1pYMQ0zzLUMpgEd6qqRwBtJe+rigYC6ddvuqxhiKLxbfdRtNpMiqaG6kqYyJ9fux0z46B0v2KKMoaFXNS4yWXJqHqqNyXZ7pJx6Hdy81+1Dz3rn5As8cHQvkGI19HL3y5SzXkrI1bmRGA8GTw97IxmQKmCXE6tcSWjkxNlMG1TgzYk/kdS9uk9wefvkivAPeJBP9pSxy7mx8VNA1G+Vpowhbys6S0dktdl9+yq7Hlkocv0M3Y1ao9dTlRNWCcoi3ofdqs+j7Ftnomy7Cc6dej94ca0yX3K4qbd7aGiLpuBxB0MfhRdH8JH0y63IwBVsN42X2xmqi/cGQNq27IeHvKNTQ64cGMipbcW/wKhjyPIiAdi7jnf3UqNBM04TcICoCEczmK+NegxDG2sHQNFFq19k= \
  --clipboard
  
# with the result in your clipboard, update docker/.env for your connection string
```

## Useful Things

### Generate SQL Server Connection Strings
Get the login information from Keeper (or from Hashi Vault: http://10.101.0.251:8200/ui/vault/auth?with=okta). SQL Server dynamic ports are [here](https://aspencapital.atlassian.net/wiki/spaces/DEV/pages/2158919715/Laptop+Network+Access) in Confluence.

```bash
./tools/mwaa_connection.py --clipboard \
  -c mssql \
  -l saNodeQA \
  -p 'single_quoted_password' \
  --host devserver.flanderscapital.com\\qa2 \
  --port 51534
```

### Test a Task with Airflow CLI

```bash
# shell into the airflow container with docker
airflow tasks test -h

# dag_id: mssql_test
# task_id: selecting_table
# execution_date: 2020-01-01
airflow tasks test mssql_test selecting_table 2020-01-01
```

# References
* [Example Airflow DAGs](https://github.com/airflow-plugins/Example-Airflow-DAGs)
* [Linting & Formatting](https://py-vscode.readthedocs.io/en/latest/files/linting.html)
* [Setup Black and Isort in VSCode](https://cereblanco.medium.com/setup-black-and-isort-in-vscode-514804590bf9)
