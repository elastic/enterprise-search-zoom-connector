#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run an incremental sync against the source.

    It will attempt to sync documents that have changed or have been added in the
    third-party system recently and ingest them into Enterprise Search instance.

    Recency is determined by the time when the last successful incremental or full job
    was ran.
"""

from .base_command import BaseCommand

INDEXING_TYPE = "incremental"


class IncrementalSyncCommand(BaseCommand):
    """This class start executions of incrementalsync feature."""

    def __init__(self, args):
        super().__init__(args)
        self.logger.debug("Initializing the incremental sync")

    def execute(self):
        """This function execute the start function."""

        self.logger.debug("Executing the incremental sync..")
