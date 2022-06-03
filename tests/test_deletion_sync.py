#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
from unittest.mock import MagicMock, Mock

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.deletion_sync_command import DeletionSyncCommand  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa

USERS = "users"
MEETINGS = "meetings"
GROUPS = "groups"
CHANNELS = "channels"
AUTH_BASE_URL = "https://zoom.us/oauth/token?grant_type="

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)

SECRETS_JSON_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "ees_zoom",
    "secrets.json",
)


def settings(requests_mock):
    """This function loads configuration from the file and returns it,
    it also mocks the zoom refresh token generation API response.
    :param requests_mock: fixture for requests.get calls.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    logger = logging.getLogger("unit_test_deletion_sync")
    new_refresh_token = "new_dummy_refresh_token"
    old_refresh_token = "old_dummy_refresh_token"
    access_token = "dummy_access_token"
    json_response = {"refresh_token": new_refresh_token, "access_token": access_token}
    zoom_client_object = ZoomClient(configuration, logger)
    zoom_client_object.secrets_storage.get_refresh_token = MagicMock(
        return_value=old_refresh_token
    )
    url = (
        AUTH_BASE_URL
        + f"authorization_code&code={zoom_client_object.authorization_code}"
        f"&redirect_uri={zoom_client_object.redirect_uri}"
    )
    headers = zoom_client_object.get_headers()
    requests_mock.post(
        url,
        headers=headers,
        json=json_response,
        status_code=200,
    )
    return configuration, logger


@pytest.mark.parametrize(
    "deleted_ids, storage_with_collection, updated_storage_with_collection",
    [
        (
            ["844424930334011", "543528180028451862"],
            {
                "global_keys": [
                    {"id": "844424930334011"},
                    {"id": "543528180028451862"},
                ],
                "delete_keys": [
                    {"id": "844424930334011"},
                    {"id": "543528180028451862"},
                ],
            },
            {
                "global_keys": [],
                "delete_keys": [
                    {"id": "844424930334011"},
                    {"id": "543528180028451862"},
                ],
            },
        )
    ],
)
def test_delete_documents(
    requests_mock,
    deleted_ids,
    storage_with_collection,
    updated_storage_with_collection,
):
    """Test that deletion_sync_command deletes objects from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param deleted_ids: list of deleted documents ids from zoom.
    :param storage_with_collection: objects documents dictionary.
    :param updated_storage_with_collection: updated objects documents dictionary.
    """
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    deletion_sync_obj.workplace_search_client.delete_documents = Mock()
    deletion_sync_obj.zoom_client.get_token()
    assert (
        deletion_sync_obj.delete_documents(deleted_ids, storage_with_collection)
        == updated_storage_with_collection
    )


@pytest.mark.parametrize(
    "user_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {"code": 1001, "message": "User does not exist: 844424930334011."},
        )
    ],
)
def test_collect_deleted_ids_for_users_positive(
    requests_mock,
    user_id_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes users object from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param user_id_list: list of user_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/users/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=404,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_ids(user_id_list, USERS)
    assert user_id_list == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "user_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {
                "id": "844424930334011",
                "type": "users",
            },
        )
    ],
)
def test_collect_deleted_ids_for_users_negative(
    requests_mock,
    user_id_list,
    deletion_response,
):
    """Test that deletion_sync_command won't delete users object from Enterprise Search if it exist in Zoom.
    :param requests_mock: fixture for requests.get calls.
    :param user_id_list: list of user_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    config, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/users/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=200,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_ids(user_id_list, USERS)
    assert [] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "role_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {"code": 1001, "message": "Role does not exist: 844424930334011."},
        )
    ],
)
def test_collect_deleted_roles_ids_positive(
    requests_mock,
    role_id_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes roles object from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param role_id_list: list of role_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/roles/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=300,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_roles_ids(role_id_list)
    assert role_id_list == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "role_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {
                "id": "844424930334011",
                "type": "roles",
            },
        )
    ],
)
def test_collect_deleted_roles_ids_negative(
    requests_mock,
    role_id_list,
    deletion_response,
):
    """Test that deletion_sync_command won't delete roles object from Enterprise Search if it exist in Zoom.
    :param requests_mock: fixture for requests.get calls.
    :param role_id_list: list of role_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/roles/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=200,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_roles_ids(role_id_list)
    assert [] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "group_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {"code": 1001, "message": "Group does not exist: 844424930334011."},
        )
    ],
)
def test_collect_deleted_ids_for_groups_positive(
    requests_mock,
    group_id_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes groups object from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param group_id_list: list of group_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    config, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/groups/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=404,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_ids(group_id_list, GROUPS)
    assert group_id_list == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "group_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {
                "id": "844424930334011",
                "type": "groups",
            },
        )
    ],
)
def test_collect_deleted_ids_for_groups_negative(
    requests_mock,
    group_id_list,
    deletion_response,
):
    """Test that deletion_sync_command won't delete groups object from Enterprise Search if it exist in Zoom.
    :param requests_mock: fixture for requests.get calls.
    :param group_id_list: list of group_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/groups/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=200,
    )
    deletion_sync_obj.zoom_client.get_token()
    deletion_sync_obj.collect_deleted_ids(group_id_list, GROUPS)
    assert [] == deletion_sync_obj.global_deletion_ids
