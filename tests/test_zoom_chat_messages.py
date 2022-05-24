#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import datetime
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
from ees_zoom.constant import RFC_3339_DATETIME_FORMAT # noqa
from ees_zoom.zoom_chat_messages import ZoomChatMessages # noqa
from ees_zoom.zoom_client import ZoomClient # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
FILES = "files"
CHATS = "chats"
CHATS_SCHEMA = {
    "created_at": "date_time",
    "description": "message",
    "id": "id",
}
FILES_SCHEMA = {
    "created_at": "date_time",
    "id": "file_id",
    "size": "file_size",
    "title": "file_name",
    "url": "download_url",
}


def settings():
    """This method loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    :returns zoom_enterprise_search_mappings: dictionary containing mappings from zoom_user_id to enterprise_user_id
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    zoom_enterprise_search_mappings = {
        "dummy_id_1": ["ent_dummy_id_1", "ent_dummy_id_1_2"],
        "dummy_id_2": ["ent_dummy_id_2"],
    }
    logger = logging.getLogger("unit_test_chat_messages")
    return configuration, logger, zoom_enterprise_search_mappings


def create_chats_messages_object():
    """This method create ZoomChatMessages object for test.
    :returns ZoomChatMessages: Instance of ZoomChatMessages.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomChatMessages(
        configs, logger, zoom_client, zoom_enterprise_search_mappings
    )


@mock.patch("requests.get")
def test_get_chats_details_documents_positive(mock_request_get):
    """Test for generating chats documents, generated from data fetched from Zoom.
    :param mock_request_get: mock patch for requests.get calls.
    """

    chats_messages_object = create_chats_messages_object()
    dummy_users_data = ["dummy_id_1"]
    dummy_chats_data_with_next_page_token = {
        "from": "2022-02-07T06:26:44Z",
        "to": "2022-04-16T07:56:12Z",
        "page_size": 50,
        "next_page_token": "next_page_token",
        "messages": [
            {
                "id": "dummy_id1",
                "message": "Dummy message",
                "sender": "dummy@dummy.co.dumyy",
                "date_time": "2022-04-11T06:05:27Z",
                "timestamp": 12331123123122,
            },
        ],
    }
    dummy_chats_data_without_next_page_token = {
        "from": "2022-02-07T06:26:44Z",
        "to": "2022-04-16T07:56:12Z",
        "page_size": 50,
        "next_page_token": "",
        "messages": [
            {
                "id": "dummy_id2",
                "message": "Dummy message2",
                "sender": "dummy@dummy.co.dumyy",
                "date_time": "2022-04-11T06:05:27Z",
                "timestamp": 12331123123122,
            },
        ],
    }
    expected_response = [
        {
            "type": "chats",
            "parent_id": "dummy_id_1",
            "created_at": "2022-04-11T06:05:27Z",
            "description": "Dummy message",
            "id": "dummy_id1",
            "body": "Message : Dummy message",
            "url": "https://zoom.us/account/archivemsg/search#/list",
            "_allow_permissions": [
                "ChatMessage:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "chats",
            "parent_id": "dummy_id_1",
            "created_at": "2022-04-11T06:05:27Z",
            "description": "Dummy message2",
            "id": "dummy_id2",
            "body": "Message : Dummy message2",
            "url": "https://zoom.us/account/archivemsg/search#/list",
            "_allow_permissions": [
                "ChatMessage:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2022-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True

    dummy_chats_data_without_next_page_token = json.dumps(
        dummy_chats_data_without_next_page_token
    )
    dummy_chats_data_with_next_page_token = json.dumps(
        dummy_chats_data_with_next_page_token
    )
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = dummy_chats_data_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = dummy_chats_data_without_next_page_token
    mock_request_get.side_effect = mock_response
    response = chats_messages_object.get_chats_details_documents(
        dummy_users_data,
        CHATS_SCHEMA,
        start_time,
        end_time,
        enable_permission,
    )
    assert response["type"] == CHATS
    assert response["data"] == expected_response


@mock.patch("requests.get")
def test_get_chats_details_documents_negative(mock_request_get):
    """test case where Zoom is down
    :param mock_request_get: mock patch for requests.get calls.
    """
    dummy_users_data = ["dummy_user1"]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2022-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    chats_messages_object = create_chats_messages_object()
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response.raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(BaseException):
        chats_messages_object.get_chats_details_documents(
            dummy_users_data,
            CHATS_SCHEMA,
            start_time,
            end_time,
            enable_permission,
        )
