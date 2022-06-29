#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import json
import logging
import os
import sys
import time
from unittest import mock
from unittest.mock import Mock

import pytest
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.zoom_channels import ZoomChannels  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
CHANNELS = "channels"
SCHEMA = {
    "id": "id",
    "title": "name",
}


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    :returns zoom_enterprise_search_mappings: dictionary containing mappings from zoom_user_id to enterprise_user_id
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    zoom_enterprise_search_mappings = {
        "dummy_id_1": ["ent_dummy_id_1", "ent_dummy_id_1_2"],
        "dummy_id_2": ["ent_dummy_id_2"],
    }
    logger = logging.getLogger("unit_test_channels")
    return configuration, logger, zoom_enterprise_search_mappings


def create_channels_object():
    """This function create channels object for test.
    :returns ZoomChannels: Instance of ZoomChannels.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomChannels(configs, logger, zoom_client, zoom_enterprise_search_mappings)


@mock.patch("requests.get")
def test_get_channels_details_documents(mock_request_get):
    """Test for generating channels documents, generated from data fetched from Zoom.
    :param mock_request_get: mock patch for requests.get calls.
    """
    # Setup
    channels_object = create_channels_object()
    dummy_users_data = [
        {
            "id": "dummy_id_1",
            "first_name": "user1",
            "last_name": "abc",
            "email": "dummy@dummy.com",
            "type": 2,
            "pmi": 12341234,
            "timezone": "Planet/Earth",
            "verified": 1,
            "dept": "",
            "created_at": "2020-05-11T06:20:41Z",
            "last_login_time": "2222-22-22T22:22:22Z",
            "last_client_version": "5.9.1.3506(mac)",
            "pic_url": "https://dummy_user_id1_url.com/",
            "language": "en-US",
            "phone_number": "",
            "status": "Passive",
            "role_id": "0",
        }
    ]
    mock_resp_with_next_page_token = {
        "total_records": 1,
        "page_size": 50,
        "next_page_token": "dummy_next_page_token",
        "channels": [
            {
                "id": "dummy_id1",
                "jid": "dummy_id1@dummy.com",
                "name": "dummy_name",
                "type": 20000,
                "channel_settings": {
                    "new_members_can_see_previous_messages_files": "dummy permissions1",
                    "allow_to_add_external_users": "dummy_permissions2",
                    "posting_permissions": "dummy_permissions3",
                },
            }
        ],
    }
    mock_resp_without_next_page_token = {
        "total_records": 1,
        "page_size": 50,
        "next_page_token": "",
        "channels": [
            {
                "id": "dummy_id2",
                "jid": "dummy_id2@dummy.com",
                "name": "dummy_name_2",
                "type": 40000,
                "channel_settings": {
                    "new_members_can_see_previous_messages_files": "dummy permissions4",
                    "allow_to_add_external_users": "dummy_permissions5",
                    "posting_permissions": "dummy_permissions6",
                },
            }
        ],
    }
    expected_response = [
        {
            "type": "channels",
            "id": "dummy_id1",
            "title": "dummy_name",
            "body": "{'new_members_can_see_previous_messages_files': 'dummy permissions1', 'allow_to_add_external_users': 'dummy_permissions2', 'posting_permissions': 'dummy_permissions3'}",
            "url": "https://zoom.us/account/imchannel/old#/member/dummy_id1",
            "_allow_permissions": [
                "ChatChannel:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "channels",
            "id": "dummy_id2",
            "title": "dummy_name_2",
            "body": "{'new_members_can_see_previous_messages_files': 'dummy permissions4', 'allow_to_add_external_users': 'dummy_permissions5', 'posting_permissions': 'dummy_permissions6'}",
            "url": "https://zoom.us/account/imchannel/old#/member/dummy_id2",
            "_allow_permissions": [
                "ChatChannel:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
    ]
    enable_permission = True
    mock_resp_with_next_page_token = json.dumps(mock_resp_with_next_page_token)
    mock_resp_without_next_page_token = json.dumps(mock_resp_without_next_page_token)
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = mock_resp_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = mock_resp_without_next_page_token
    mock_request_get.side_effect = mock_response

    # Execute
    response = channels_object.get_channels_details_documents(
        dummy_users_data,
        SCHEMA,
        enable_permission,
    )

    # Assert
    assert response["type"] == CHANNELS
    assert response["data"] == expected_response


@mock.patch("requests.get")
def test_get_channels_details_documents_negative(mock_request_get):
    """test case where Zoom is down
    :param mock_request_get: mock patch for requests.get calls.
    """
    # Setup
    dummy_users_data = [
        {
            "id": "dummy_id_1",
            "first_name": "user1",
            "last_name": "abc",
            "email": "dummy@dummy.com",
            "type": 2,
            "pmi": 12341234,
            "timezone": "Planet/Earth",
            "verified": 1,
            "dept": "",
            "created_at": "2020-05-11T06:20:41Z",
            "last_login_time": "2222-22-22T22:22:22Z",
            "last_client_version": "5.9.1.3506(mac)",
            "pic_url": "https://dummy_user_id1_url.com/",
            "language": "en-US",
            "phone_number": "",
            "status": "Passive",
            "role_id": "0",
        }
    ]
    enable_permission = True
    channels_object = create_channels_object()
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response.raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response

    # Execute and assert
    with pytest.raises(BaseException):
        channels_object.get_channels_details_documents(
            dummy_users_data,
            SCHEMA,
            enable_permission,
        )
