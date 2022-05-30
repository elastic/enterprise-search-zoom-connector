#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import argparse
import logging
import os
import sys
from unittest.mock import Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.bootstrap_command import BootstrapCommand  # noqa
from ees_zoom.configuration import Configuration  # noqa
from elastic_enterprise_search import WorkplaceSearch  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads config from the file and returns it."""
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_bootstrap_command")
    return configuration, logger


def test_execute(caplog):
    """Test execute method in Bootstrap file creates a content source in the Enterprise Search.
    :param caplog: records the attributes from current stage.
    """
    args = argparse.Namespace()
    args.name = "dummy"
    args.config_file = CONFIG_FILE
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    bootstrap_object = BootstrapCommand(args)
    bootstrap_object.workplace_search_client.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )
    bootstrap_object.execute()
    assert "Created ContentSource with ID 1234." in caplog.text
