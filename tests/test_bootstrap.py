#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import argparse
import os
import sys
from unittest.mock import Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.bootstrap_command import BootstrapCommand  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def test_execute(caplog):
    """Test execute method in Bootstrap file creates a content source in the Enterprise Search."""
    args = argparse.Namespace()
    args.name = "dummy"
    args.config_file = CONFIG_FILE
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    bootstrap_obj = BootstrapCommand(args)
    bootstrap_obj.workplace_search_client.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )
    bootstrap_obj.execute()
    assert "Created ContentSource with ID 1234." in caplog.text


def test_execute_with_user_argument(caplog):
    """Test execute method in Bootstrap file creates a content source using user argument in the Enterprise Search."""
    args = argparse.Namespace()
    args.name = "dummy"
    args.user = "user1"
    args.password = "user123"
    args.config_file = CONFIG_FILE
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    bootstrap_obj = BootstrapCommand(args)
    bootstrap_obj.workplace_search_client.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )
    bootstrap_obj.execute()
    assert "Created ContentSource with ID 1234." in caplog.text
