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
from ees_zoom.deletion_sync_command import DeletionSyncCommand  # noqa
from ees_zoom.sync_zoom import SyncZoom  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa
from support import get_args  # noqa

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
def test_collect_multithreaded_objects_ids_positive(
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
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.get_token()
    deletion.collect_multithreaded_objects_ids(objects_ids_list)
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
def test_collect_multithreaded_objects_ids_negative(
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
    _, _ = settings(requests_mock)
    args = get_args("DeletionSyncCommand")
    deletion = DeletionSyncCommand(args)
    mock1.return_value = [response_list]
    deletion.create_jobs = Mock(return_value=response_list)
    SyncZoom.get_all_users_from_zoom = Mock()
    deletion.zoom_client.get_token()
    deletion.collect_multithreaded_objects_ids(objects_ids_list)
    assert [] == deletion.global_deletion_ids
