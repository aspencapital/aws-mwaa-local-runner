#!/usr/bin/env python

import argparse
import re
import subprocess
import urllib.parse

# https://stackoverflow.com/a/43357954


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main(args):

    # base connection string
    conn_string = '{0}://{1}:{2}@{3}'.format(
        args.conn_type,
        urllib.parse.quote_plus(args.login),
        urllib.parse.quote_plus(args.password),
        args.host)

    if (args.extras):
        # capture key/value of extra
        p = re.compile('^([^=]+)=(.*)')

        for i, extra in enumerate(args.extras):
            # prefix
            conn_string += '?' if i == 0 else '&'

            # split key/value
            m = p.match(extra)
            key = m.group(1)
            value = m.group(2)

            conn_string += '{0}={1}'.format(key,
                                            urllib.parse.quote_plus(value))
    print('connection string:\n{}'.format(conn_string))

    if args.clipboard:
        subprocess.run("pbcopy", universal_newlines=True, input=conn_string)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conn_type', default='aws')
    parser.add_argument("--clipboard", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Copy to clipboard")
    parser.add_argument('--host', nargs='?', default='')
    parser.add_argument('-l', '--login', required=True)
    parser.add_argument('-p', '--password', required=True)
    parser.add_argument('-v', dest='verbose',
                        action='store_true', help='verbosity')
    parser.add_argument('-x', '--extras', nargs='*')
    args = parser.parse_args()
    main(args)
