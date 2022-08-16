#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
import unittest.mock
from unittest.mock import MagicMock, Mock, patch

from support import get_args

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.permission_sync_command import PermissionSyncCommand  # noqa
from ees_zoom.zoom_roles import ZoomRoles # noqa

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
    # Setup
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

    # Execute
    mock.permission_object.remove_all_permissions()

    # Assert
    mock.permission_object.remove_all_permissions.assert_called()


def test_workplace_add_permission():
    """Test that workplace_add_permission successfully add permission to Enterprise Search."""
    # Setup
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    permission_object = PermissionSyncCommand(args)
    permission_object.workplace_search_client.add_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()

    # Execute
    mock.permission_object.workplace_add_permission("user1", "permission1")

    # Assert
    mock.permission_object.workplace_add_permission.assert_called()


@patch.object(ZoomRoles, "set_list_of_roles_from_zoom")
@patch.object(ZoomRoles, "fetch_role_permissions")
@patch.object(ZoomRoles, "fetch_members_of_role")
def test_set_permissions_list(
    mock_members_of_role, mock_role_permission, mock_list_of_role
):
    """Tests the set_permission_list function for permission sync.
    :param mock_members_of_role: patch object for fetch_members_of_role
    :param mock_role_permission: patch object for fetch_role_permissions
    :param mock_list_of_role: patch object for set_list_of_roles_from_zoom
    """
    # Setup
    config, logger = settings()
    args = get_args("PermissionSyncCommand")
    permission_sync = PermissionSyncCommand(args)
    permission_sync.zoom_client.ensure_token_valid = Mock()
    roles_object = ZoomRoles(
        config,
        logger,
        permission_sync.zoom_client,
        permission_sync.zoom_enterprise_search_mappings,
    )
    mock_list_of_role.return_value = True

    with unittest.mock.patch.object(roles_object, "roles_list", MagicMock()):
        dummy_permissions = ["permission1", "permission2"]
        dummy_user_ids = ["zoom_user_id", "zoom_user_id_2"]
        mock_role_permission.return_value = dummy_permissions
        mock_members_of_role.return_value = dummy_user_ids
        permission_sync.workplace_search_client.add_user_permissions = Mock(
            return_value=True
        )

        # Execute
        permission_sync.set_permissions_list(
            permission_sync.zoom_enterprise_search_mappings
        )

        permission_sync.workplace_search_client.add_user_permissions = Mock(
            return_value=True
        )
        mock = Mock()
        mock.permission_sync.workplace_add_permission(
            dummy_user_ids[0],
            dummy_permissions.append(
                permission_sync.zoom_enterprise_search_mappings.get(dummy_user_ids[0])
            ),
        )

        # Assert
        mock.permission_sync.workplace_add_permission.assert_called()
