#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import pytest
import unittest
import unittest.mock

from ees_zoom import cli

from tests.support import get_args

class TestCli(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _pass_fixtures(self, capsys):
        self.capsys = capsys

    def test_run_with_bootstrap(self):
        for command in ["bootstrap", "full-sync", "incremental-sync", "deletion-sync", "test-connectivity"]:
            args = get_args(command)
            assert cli.run(args) == 0
