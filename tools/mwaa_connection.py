#!/usr/bin/env python

import argparse
import configparser
import os
import re
import subprocess
import urllib.parse


def str2bool(v):
    # https://stackoverflow.com/a/43357954
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def main(args):
    login = ""
    password = ""

    if args.profile:
        config = configparser.ConfigParser()
        config.read(os.path.expanduser("~/.aws/credentials"))
        login = config[args.profile]["aws_access_key_id"]
        password = config[args.profile]["aws_secret_access_key"]
        region = config[args.profile]["region"]
        token = config[args.profile]["aws_session_token"]

        # use the extras loop to process region and token
        if region:
            args.extras.append(f"region_name={region}")
        if token:
            args.extras.append(f"aws_session_token={token}")

    else:
        login = args.login
        password = args.password

    # base connection string
    conn_string = "{0}://{1}:{2}@{3}".format(
        args.conn_type,
        urllib.parse.quote_plus(login),
        urllib.parse.quote_plus(password),
        args.host,
    )

    if args.extras:
        # capture key/value of extra
        p = re.compile("^([^=]+)=(.*)")

        for i, extra in enumerate(args.extras):
            # prefix
            conn_string += "?" if i == 0 else "&"

            # split key/value
            m = p.match(extra)
            key = m.group(1)
            value = m.group(2)

            conn_string += "{0}={1}".format(key, urllib.parse.quote_plus(value))
    print("connection string:\n{}".format(conn_string))

    # mac-specific: copy result to clipboard
    if args.clipboard:
        subprocess.run("pbcopy", universal_newlines=True, input=conn_string)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a properly encoded connection string that can be loaded as an environment variable for "
        "airflow, AIRFLOW_CONN_<conn_id>."
    )
    parser.add_argument(
        "-c",
        "--conn_type",
        default="aws",
        help="connection type; e.g. aws, mssql, samba",
    )
    parser.add_argument(
        "--clipboard",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="copy to clipboard",
    )
    parser.add_argument("--host", nargs="?", default="")
    parser.add_argument("-l", "--login", default="")
    parser.add_argument("-p", "--password", default="")
    parser.add_argument(
        "--profile",
        required=False,
        help="profile name in credentials to read login, password, region, and token from, ~/.aws/credentials",
    )
    parser.add_argument(
        "-x",
        "--extras",
        nargs="*",
        default=[],
        help="extra metadata; space delimited <key>=<value> pairs",
    )
    args = parser.parse_args()
    main(args)
