#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.sync_zoom import SyncZoom  # noqa
from ees_zoom.deletion_sync_command import DeletionSyncCommand  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa
from support import get_args  # noqa

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
    access_token = "dummy_access_token"
    json_response = {"refresh_token": new_refresh_token, "access_token": access_token}
    zoom_client_object = ZoomClient(configuration, logger)
    zoom_client_object.secrets_storage.get_secrets = MagicMock(return_value=None)
    url = (
        f"{AUTH_BASE_URL}"
        f"authorization_code&code={zoom_client_object.authorization_code}"
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
                    {"id": "543528180028451862"}
                ],
                "delete_keys": [
                    {"id": "844424930334011"},
                    {"id": "543528180028451862"}
                ]
            },
            {
                "global_keys": [],
                "delete_keys": [
                    {"id": "844424930334011"},
                    {"id": "543528180028451862"}
                ]
            }
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
    # Setup
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    deletion_sync_obj.workplace_search_client.delete_documents = Mock()
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute and assert
    assert deletion_sync_obj.delete_documents(deleted_ids, storage_with_collection) == updated_storage_with_collection


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
    # Setup
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
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(user_id_list, USERS)

    # Assert
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
    # Setup
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
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(user_id_list, USERS)

    # Assert
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
    # Setup
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
        status_code=400,
    )
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_roles_ids(role_id_list)

    # Assert
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
    # Setup
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
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_roles_ids(role_id_list)

    # Assert
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
    # Setup
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
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(group_id_list, GROUPS)

    # Assert
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
    # Setup
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
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(group_id_list, GROUPS)

    # Assert
    assert [] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "meeting_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {"code": 1001, "message": "Meeting does not exist: 844424930334011."},
        )
    ],
)
def test_collect_deleted_ids_for_meetings_positive(
    requests_mock,
    meeting_id_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes meetings object from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param meeting_id_list: list of meeting_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    # Setup
    config, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/meetings/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=404,
    )
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(meeting_id_list, MEETINGS)

    # Assert
    assert meeting_id_list == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "meeting_id_list, deletion_response",
    [
        (
            ["844424930334011"],
            {
                "id": "844424930334011",
                "type": "meetings",
            },
        )
    ],
)
def test_collect_deleted_ids_for_meetings_negative(
    requests_mock,
    meeting_id_list,
    deletion_response,
):
    """Test that deletion_sync_command won't delete meetings object from Enterprise Search if it exist in Zoom.
    :param requests_mock: fixture for requests.get calls.
    :param meeting_id_list: list of meeting_id deleted from zoom.
    :param deletion_response: dictionary of mocked api response.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/meetings/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=200,
    )
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_deleted_ids(meeting_id_list, MEETINGS)

    # Assert
    assert [] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "past_meeting_id_list, delete_key_list, deletion_response",
    [
        (
            ["844424930334011"],
            [
                {
                    "id": "dummy1234",
                    "type": "past_meetings",
                    "parent_id": "844424930334011",
                    "created_at": "",
                }
            ],
            {"code": 1001, "message": "Role does not exist: 844424930334011."},
        )
    ],
)
def test_collect_past_deleted_meetings_positive(
    requests_mock,
    past_meeting_id_list,
    delete_key_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes past_meetings object from Enterprise Search.
    :param requests_mock: fixture for requests.get calls.
    :param past_meeting_id_list: list of past_meeting_id deleted from zoom.
    :param delete_key_list: list of dictionary of delete_keys exist in doc_id storage.
    :param deletion_response: dictionary of mocked api response.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/past_meetings/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=404,
    )
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_past_deleted_meetings(
        past_meeting_id_list, delete_key_list
    )

    # Assert
    assert [delete_key_list[0]["id"]] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "past_meeting_id_list, delete_key_list, deletion_response",
    [
        (
            ["844424930334011"],
            [
                {
                    "id": "dummy1234",
                    "type": "past_meetings",
                    "parent_id": "844424930334011",
                    "created_at": "",
                }
            ],
            {
                "id": "844424930334011",
                "type": "past_meetings",
            },
        )
    ],
)
def test_collect_past_deleted_meetings_negative(
    requests_mock,
    past_meeting_id_list,
    delete_key_list,
    deletion_response,
):
    """Test that deletion_sync_command won't delete past_meetings object from Enterprise Search if it exist in Zoom.
    :param requests_mock: fixture for requests.get calls.
    :param past_meeting_id_list: list of past_meeting_id deleted from zoom.
    :param delete_key_list: list of dictionary of delete_keys exist in doc_id storage.
    :param deletion_response: dictionary of mocked api response.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    deletion_sync_obj = DeletionSyncCommand(args)
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/past_meetings/844424930334011",
        headers=headers,
        json=deletion_response,
        status_code=200,
    )
    deletion_sync_obj.zoom_client.ensure_token_valid()

    # Execute
    deletion_sync_obj.collect_past_deleted_meetings(
        past_meeting_id_list, delete_key_list
    )

    # Assert
    assert [] == deletion_sync_obj.global_deletion_ids


@pytest.mark.parametrize(
    "objects_ids_list, response_list, deletion_response",
    [
        (
            ["844424930334011", "844424930334012", "844424930334013"],
            [
                {
                    "id": "844424930334011",
                    "type": "channels",
                    "parent_id": "",
                    "created_at": "",
                },
                {
                    "id": "844424930334012",
                    "type": "recordings",
                    "parent_id": "abcd1234",
                    "created_at": "",
                },
            ],
            ["844424930334013"],
        )
    ],
)
@patch.object(SyncZoom, "perform_sync")
def test_collect_channels_and_recordings_ids_positive(
    mock1,
    requests_mock,
    objects_ids_list,
    response_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes channels, recordings, chats and files object from Enterprise Search.
    :param mock1: patch object for perform_sync method.
    :param requests_mock: fixture for requests.get calls.
    :param objects_ids_list: list of objects ids deleted from zoom.
    :param response_list: list of dictionary of mocked api response.
    :param deletion_response: list of deleted documents ids.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_and_execute_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.ensure_token_valid()

    # Execute
    deletion.collect_channels_and_recordings_ids(objects_ids_list)

    # Assert
    assert deletion.global_deletion_ids == deletion_response


@pytest.mark.parametrize(
    "objects_ids_list, response_list",
    [
        (
            ["844424930334011", "844424930334012"],
            [
                {
                    "id": "844424930334011",
                    "type": "channels",
                    "parent_id": "",
                    "created_at": "",
                },
                {
                    "id": "844424930334012",
                    "type": "recordings",
                    "parent_id": "abcd1234",
                    "created_at": "",
                },
            ],
        )
    ],
)
@patch.object(SyncZoom, "perform_sync")
def test_collect_channels_and_recordings_ids_negative(
    mock1,
    requests_mock,
    objects_ids_list,
    response_list,
):
    """Test that deletion_sync_command won't delete channels, recordings, chats and files object from Enterprise Search
    if it exist in Zoom.
    :param mock1: patch object for perform_sync method.
    :param requests_mock: fixture for requests.get calls.
    :param objects_ids_list: list of objects ids deleted from zoom.
    :param response_list: list of dictionary of mocked api response.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_and_execute_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.ensure_token_valid()

    # Execute
    deletion.collect_channels_and_recordings_ids(objects_ids_list)

    # Assert
    assert [] == deletion.global_deletion_ids


@pytest.mark.parametrize(
    "objects_ids_list, response_list, deletion_response",
    [
        (
            ["844424930334011", "844424930334012", "844424930334013"],
            [
                {
                    "id": "844424930334011",
                    "type": "chats",
                    "parent_id": "",
                    "created_at": "",
                },
                {
                    "id": "844424930334012",
                    "type": "files",
                    "parent_id": "abcd1234",
                    "created_at": "",
                },
            ],
            ["844424930334013"],
        )
    ],
)
@patch.object(SyncZoom, "perform_sync")
def test_collect_chats_and_files_ids_positive(
    mock1,
    requests_mock,
    objects_ids_list,
    response_list,
    deletion_response,
):
    """Test that deletion_sync_command deletes chats and files object from Enterprise Search.
    :param mock1: patch object for perform_sync method.
    :param requests_mock: fixture for requests.get calls.
    :param objects_ids_list: list of objects ids deleted from zoom.
    :param response_list: list of dictionary of mocked api response.
    :param deletion_response: list of deleted documents ids.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_and_execute_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.ensure_token_valid()

    # Execute
    deletion.collect_channels_and_recordings_ids(objects_ids_list)

    # Assert
    assert deletion.global_deletion_ids == deletion_response


@pytest.mark.parametrize(
    "objects_ids_list, response_list",
    [
        (
            ["844424930334011", "844424930334012"],
            [
                {
                    "id": "844424930334011",
                    "type": "chats",
                    "parent_id": "",
                    "created_at": "",
                },
                {
                    "id": "844424930334012",
                    "type": "files",
                    "parent_id": "abcd1234",
                    "created_at": "",
                },
            ],
        )
    ],
)
@patch.object(SyncZoom, "perform_sync")
def test_collect_chats_and_files_ids_negative(
    mock1,
    requests_mock,
    objects_ids_list,
    response_list,
):
    """Test that deletion_sync_command won't delete chats and files object from Enterprise Search
    if it exist in Zoom.
    :param mock1: patch object for perform_sync method.
    :param requests_mock: fixture for requests.get calls.
    :param objects_ids_list: list of objects ids deleted from zoom.
    :param response_list: list of dictionary of mocked api response.
    """
    # Setup
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_and_execute_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.ensure_token_valid()

    # Execute
    deletion.collect_channels_and_recordings_ids(objects_ids_list)

    # Assert
    assert [] == deletion.global_deletion_ids
