#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import os
import sys
from collections import namedtuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def get_args(command_name, *args):
    """generate args for testing cli file
    :param command_name: name of the command to execute.
    """
    args = namedtuple("args", "verbose quiet duration exception")
    args.cmd = command_name

    args.config_file = CONFIG_FILE
    return args
