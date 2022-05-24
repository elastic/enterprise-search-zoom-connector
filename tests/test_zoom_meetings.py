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

import pytest
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest import mock  # noqa
from unittest.mock import Mock  # noqa

from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.constant import RFC_3339_DATETIME_FORMAT  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa
from ees_zoom.zoom_meetings import ZoomMeetings  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
MEETINGS = "meetings"
SCHEMA = {
    "created_at": "created_at",
    "id": "id",
    "title": "topic",
}


def settings():
    """This Method loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    :returns zoom_enterprise_search_mappings: dictionary containing mappings from zoom_user_id to enterprise_user_id
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    zoom_enterprise_search_mappings = {
        "dummy_id_1": ["ent_dummy_id_1", "ent_dummy_id_1_2"],
        "dummy_id_2": ["ent_dummy_id_2"],
    }
    logger = logging.getLogger("unit_test_meetings")
    return configuration, logger, zoom_enterprise_search_mappings


def create_meetings_object():
    """This Method create ZoomMeetings object for test.
    :returns ZoomMeetings: Instance of ZoomMeetings.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomMeetings(configs, logger, zoom_client, zoom_enterprise_search_mappings)


@mock.patch("requests.get")
def test_get_meetings_details_documents(mock_request_get):
    """Test for generating meetings documents, generated from data fetched from Zoom.
    :param mock_request_get: mock patch for requests.get calls.
    """
    meetings_object = create_meetings_object()
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
        "page_size": 1,
        "total_records": 1,
        "next_page_token": "dummy_next_page",
        "meetings": [
            {
                "uuid": "dummy_uuid__1",
                "id": 123123123,
                "host_id": "dummy_id_1",
                "topic": "its dummy meeting",
                "type": 1,
                "start_time": "2020-06-09T06:00:00Z",
                "duration": 19,
                "timezone": "Planet/Earth",
                "created_at": "2020-06-08T05:46:28Z",
                "join_url": "https://dummy.com/meetings/mydummy_1",
            }
        ],
    }
    mock_resp_without_next_page_token = {
        "page_size": 1,
        "total_records": 1,
        "next_page_token": "",
        "meetings": [
            {
                "uuid": "dummy_uuid__2",
                "id": 222111333,
                "host_id": "dummy_id_1",
                "topic": "its dummy meeting2",
                "type": 1,
                "start_time": "2020-06-10T06:00:00Z",
                "duration": 19,
                "timezone": "Planet/Earth",
                "created_at": "2020-06-09T05:46:28Z",
                "join_url": "https://dummy.com/meetings/mydummy_2",
            }
        ],
    }
    expected_response = [
        {
            "type": "meetings",
            "parent_id": "dummy_id_1",
            "created_at": "2020-06-08T05:46:28Z",
            "id": 123123123,
            "title": "its dummy meeting",
            "body": "Meeting Host : dummy_id_1\nMeeting Type : An instant meeting",
            "url": "https://zoom.us/user/dummy_id_1/meeting/123123123",
            "_allow_permissions": ["User:Read", "ent_dummy_id_1", "ent_dummy_id_1_2"],
        },
        {
            "type": "meetings",
            "parent_id": "dummy_id_1",
            "created_at": "2020-06-09T05:46:28Z",
            "id": 222111333,
            "title": "its dummy meeting2",
            "body": "Meeting Host : dummy_id_1\nMeeting Type : An instant meeting",
            "url": "https://zoom.us/user/dummy_id_1/meeting/222111333",
            "_allow_permissions": ["User:Read", "ent_dummy_id_1", "ent_dummy_id_1_2"],
        },
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    is_meetings_in_objects = True
    mock_resp_with_next_page_token = json.dumps(mock_resp_with_next_page_token)
    mock_resp_without_next_page_token = json.dumps(mock_resp_without_next_page_token)
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = mock_resp_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = mock_resp_without_next_page_token
    mock_request_get.side_effect = mock_response
    response = meetings_object.get_meetings_details_documents(
        dummy_users_data,
        SCHEMA,
        start_time,
        end_time,
        is_meetings_in_objects,
        enable_permission,
    )
    assert response["type"] == MEETINGS
    assert response["data"] == expected_response


@mock.patch("requests.get")
def test_get_meetings_details_documents_negative(mock_request_get):
    """test case where Zoom is down.
    :param mock_request_get: fixture for requests GET call.
    """
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
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    is_meetings_in_objects = True
    meetings_object = create_meetings_object()
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response.raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(BaseException):
        meetings_object.get_meetings_details_documents(
            dummy_users_data,
            SCHEMA,
            start_time,
            end_time,
            is_meetings_in_objects,
            enable_permission,
        )
