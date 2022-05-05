#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a full sync against the source.

    It will attempt to sync absolutely all documents that are available in the
    third-party system and ingest them into Enterprise Search instance.
"""

from .base_command import BaseCommand


class FullSyncCommand(BaseCommand):
    """This class start executions of fullsync feature."""

    def __init__(self, args):
        super().__init__(args)
        self.logger.debug("Initializing the full sync")

    def execute(self):
        """This function execute the start function."""

        self.logger.debug("Executing the full sync..")
