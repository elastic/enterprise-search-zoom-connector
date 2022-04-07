#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
from collections import namedtuple


def get_args(command_name, *args):
    args = namedtuple("args", "verbose quiet duration exception")
    args.cmd = command_name

    return args
