#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Cli module contains entry points to the connector.

Each method provides a way to make an interaction
between Elastic Enterprise Search and remote system.

For example, full-sync provides a command that will attempt to sync
all data from remote system to Elastic Enterprise Search.

See each individual command for the description.
"""

from argparse import ArgumentParser

CMD_BOOTSTRAP = "bootstrap"
CMD_FULL_SYNC = "full-sync"
CMD_INCREMENTAL_SYNC = "incremental-sync"
CMD_DELETION_SYNC = "deletion-sync"
CMD_TEST_CONNECTIVITY = "test-connectivity"


def _parser():
    parser = ArgumentParser(prog="run_connector")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    bootstrap = subparsers.add_parser(CMD_BOOTSTRAP)
    bootstrap.add_argument(
        "-n",
        "--name",
        required=True,
        type=str,
        metavar="CONTENT_SOURCE_NAME",
        help="Name of the content source to be created",
    )
    bootstrap.add_argument(
        "-u",
        "--user",
        required=False,
        type=str,
        metavar="ENTERPRISE_SEARCH_ADMIN_USER_NAME",
        help="Username of the workplace search admin account",
    )

    subparsers.add_parser(CMD_FULL_SYNC)
    subparsers.add_parser(CMD_INCREMENTAL_SYNC)
    subparsers.add_parser(CMD_DELETION_SYNC)
    subparsers.add_parser(CMD_TEST_CONNECTIVITY)

    return parser


def main(args=None):
    parser = _parser()
    args = parser.parse_args(args=args)

    return run(args)


def run(args):
    if args.cmd == CMD_BOOTSTRAP:
        print("Running bootstrap")
    elif args.cmd == CMD_FULL_SYNC:
        print("Running full sync")
    elif args.cmd == CMD_INCREMENTAL_SYNC:
        print("Running incremental sync")
    elif args.cmd == CMD_DELETION_SYNC:
        print("Running deletion sync")
    elif args.cmd == CMD_TEST_CONNECTIVITY:
        print("Running connectivity test")
    return 0
