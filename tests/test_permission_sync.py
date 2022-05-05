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


from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.permission_sync_command import PermissionSyncCommand  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_permission_sync")
    return configuration, logger


def test_remove_all_permissions():
    """Test that remove_all_permissions remove all permissions from Enterprise Search."""
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    permission_object = PermissionSyncCommand(args)
    mocked_respose = {"results": [{"user": "user1", "permissions": "permission1"}]}
    permission_object.workplace_search_client.list_permissions = Mock(
        return_value=mocked_respose
    )
    permission_object.workplace_search_client.remove_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()
    mock.permission_object.remove_all_permissions()
    mock.permission_object.remove_all_permissions.assert_called()


def test_workplace_add_permission():
    """Test that workplace_add_permission successfully add permission to Enterprise Search."""
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    permission_object = PermissionSyncCommand(args)
    permission_object.workplace_search_client.add_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()
    mock.permission_object.workplace_add_permission("user1", "permission1")
    mock.permission_object.workplace_add_permission.assert_called()