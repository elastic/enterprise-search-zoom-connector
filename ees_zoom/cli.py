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

import getpass
import os
from argparse import ArgumentParser

from .bootstrap_command import BootstrapCommand
from .deletion_sync_command import DeletionSyncCommand
from .full_sync_command import FullSyncCommand
from .incremental_sync_command import IncrementalSyncCommand
from .permission_sync_command import PermissionSyncCommand

CMD_BOOTSTRAP = "bootstrap"
CMD_FULL_SYNC = "full-sync"
CMD_INCREMENTAL_SYNC = "incremental-sync"
CMD_DELETION_SYNC = "deletion-sync"
CMD_PERMISSION_SYNC = "permission-sync"


commands = {
    CMD_BOOTSTRAP: BootstrapCommand,
    CMD_FULL_SYNC: FullSyncCommand,
    CMD_INCREMENTAL_SYNC: IncrementalSyncCommand,
    CMD_DELETION_SYNC: DeletionSyncCommand,
    CMD_PERMISSION_SYNC: PermissionSyncCommand,
}


def _parser():
    """Get a configured parser for the module.
    This method will initialize argument parser with a list
    of avaliable commands and their options."""
    parser = ArgumentParser(prog="ees_zoom")
    parser.add_argument(
        "-c",
        "--config-file",
        type=str,
        metavar="CONFIGURATION_FILE_PATH",
        help="path to the configuration file",
    )
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True
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
    subparsers.add_parser(CMD_PERMISSION_SYNC)
    return parser


def main(args=None):
    """Entry point for the connector."""
    if args is None:
        parser = _parser()
        args = parser.parse_args()

    if args.cmd == CMD_BOOTSTRAP and args.user:
        args.password = getpass.getpass(prompt="Password: ", stream=None)

    if not args.config_file:
        args.config_file = os.path.join(
            os.path.expanduser("~"), ".local", "config", "zoom_connector.yml"
        )

    run(args)


def run(args):
    """Run the command from the parsed args.

    This method takes already parsed and validated arguments
    and attempts to run the command with specified arguments."""
    if args.cmd == CMD_BOOTSTRAP:
        print("Running bootstrap")
    elif args.cmd == CMD_FULL_SYNC:
        print("Running full sync")
    elif args.cmd == CMD_INCREMENTAL_SYNC:
        print("Running incremental sync")
    elif args.cmd == CMD_DELETION_SYNC:
        print("Running deletion sync")
    commands[args.cmd](args).execute()
    return 0
