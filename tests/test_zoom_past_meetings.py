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
from ees_zoom.constant import RFC_3339_DATETIME_FORMAT  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa
from ees_zoom.zoom_past_meetings import ZoomPastMeetings  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
PAST_MEETINGS = "past_meetings"
SCHEMA = {
    "created_at": "start_time",
    "id": "uuid",
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
    logger = logging.getLogger("unit_test_past_meetings")
    return configuration, logger, zoom_enterprise_search_mappings


def create_past_meetings_object():
    """This Method create ZoomPastMeeting object for test.
    :returns ZoomPastMeetings: Instance of ZoomPastMeetings.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomPastMeetings(
        configs, logger, zoom_client, zoom_enterprise_search_mappings
    )


@mock.patch("requests.get")
def test_get_past_meetings_details_documents_positive(mock_request_get):
    """Test for generating past-meetings documents,using data fetched from Zoom.
    this case covers scenario where there are more than one participants.
    :param requests_mock: fixture for requests.get calls.
    """

    past_meetings_object = create_past_meetings_object()
    dummy_meetings_data = [
        {
            "uuid": "dummy_uuid_1",
            "id": 1231231123,
            "host_id": "dummy_id_1",
            "topic": "its dummy meeting2",
            "type": 1,
            "start_time": "2020-06-10T06:00:00Z",
            "duration": 120,
            "timezone": "Planet/Earth",
            "created_at": "2020-06-09T05:46:28Z",
            "join_url": "https://dummy.com/meetings/mydummy_2",
        }
    ]
    dummy_past_meetings_data = {
        "uuid": "dummy_uuid_1",
        "id": 1231231123,
        "host_id": "dummy_id_1",
        "type": 1,
        "topic": "its dummy meeting2",
        "user_name": "dummy username 1",
        "user_email": "dummy@dumb.com",
        "start_time": "2020-06-10T06:00:00Z",
        "end_time": "2020-05-12T06:20:41Z",
        "duration": 120,
        "total_minutes": 222,
        "participants_count": 231,
        "dept": "",
        "source": "Dummy institute",
    }
    dummy_participants_data_with_next_page_token = {
        "page_count": 1,
        "page_size": 300,
        "total_records": 2,
        "next_page_token": "next_page_token",
        "participants": [
            {
                "id": "dummy_participant_id1",
                "user_id": "16778240",
                "name": "dummy_user_1",
                "user_email": "dummy_user_1@dummy.com",
                "join_time": "1111-11-11T11:11:11Z",
                "leave_time": "1111-11-11T12:11:11Z",
                "duration": 1111,
                "attentiveness_score": "dummy",
                "failover": "false",
                "status": "dummy_status",
                "customer_key": "dummy_dummy_1",
            },
        ],
    }
    dummy_participants_data_without_next_page_token = {
        "page_count": 2,
        "page_size": 300,
        "total_records": 2,
        "next_page_token": "",
        "participants": [
            {
                "id": "dummy_participant_id2",
                "user_id": "16778240",
                "name": "dummy_user_2",
                "user_email": "dummy_user_2@dummy.com",
                "join_time": "1111-11-11T11:11:11Z",
                "leave_time": "1111-11-11T12:11:11Z",
                "duration": 2222,
                "attentiveness_score": "dummy2",
                "failover": "false",
                "status": "dummy_status2",
                "customer_key": "dummy_dummy_2",
            },
        ],
    }
    expected_response = [
        {
            "type": "past_meetings",
            "parent_id": "1231231123",
            "created_at": "2020-06-10T06:00:00Z",
            "id": "dummy_uuid_1",
            "title": "its dummy meeting2",
            "body": "Meeting Duration:120\nMeeting Type:An instant meeting\nMeeting Participants : [{'id': 'dummy_participant_id1', 'name': 'dummy_user_1', 'join_time': '1111-11-11T11:11:11Z', 'leave_time': '1111-11-11T12:11:11Z', 'duration': 1111}, {'id': 'dummy_participant_id2', 'name': 'dummy_user_2', 'join_time': '1111-11-11T11:11:11Z', 'leave_time': '1111-11-11T12:11:11Z', 'duration': 2222}]",
            "url": "https://zoom.us/user/dummy_id_1/meeting/1231231123",
            "_allow_permissions": ["User:Read", "ent_dummy_id_1", "ent_dummy_id_1_2"],
        }
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    dummy_past_meetings_data = json.dumps(dummy_past_meetings_data)
    dummy_participants_data_with_next_page_token = json.dumps(
        dummy_participants_data_with_next_page_token
    )
    dummy_participants_data_without_next_page_token = json.dumps(
        dummy_participants_data_without_next_page_token
    )
    mock_response = [Mock(), Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = dummy_past_meetings_data
    mock_response[1].status_code = 200
    mock_response[1].text = dummy_participants_data_with_next_page_token
    mock_response[2].status_code = 200
    mock_response[2].text = dummy_participants_data_without_next_page_token
    mock_request_get.side_effect = mock_response
    response = past_meetings_object.get_past_meetings_details_documents(
        dummy_meetings_data,
        SCHEMA,
        start_time,
        end_time,
        enable_permission,
    )
    assert response["type"] == PAST_MEETINGS
    assert response["data"] == expected_response


@mock.patch("requests.get")
def test_get_past_meetings_details_documents_negative(mock_request_get):
    """test case where meeting id is not past-meeting or Zoom is down.
    :param mock_request_get: mock patch for requests.get calls.
    """
    dummy_meetings_data = [
        {
            "uuid": "dummy_uuid_1",
            "id": 1231231123,
            "host_id": "dummy_id_1",
            "topic": "its dummy meeting2",
            "type": 1,
            "start_time": "2020-06-10T06:00:00Z",
            "duration": 120,
            "timezone": "Planet/Earth",
            "created_at": "2020-06-09T05:46:28Z",
            "join_url": "https://dummy.com/meetings/mydummy_2",
        }
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    past_meetings_object = create_past_meetings_object()
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response.raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(BaseException):
        past_meetings_object.get_past_meetings_details_documents(
            dummy_meetings_data,
            SCHEMA,
            start_time,
            end_time,
            enable_permission,
        )


@mock.patch("requests.get")
def test_get_past_meetings_details_documents_with_one_participant(mock_request_get):
    """Test for generating past-meetings documents,using data fetched from Zoom.
    this case covers scenario where meeting host is the only participant.
    :param mock_request_get: fixture for requests.get calls.
    """

    past_meetings_object = create_past_meetings_object()
    dummy_meetings_data = [
        {
            "uuid": "dummy_uuid_1",
            "id": 1231231123,
            "host_id": "dummy_id_1",
            "topic": "its dummy meeting2",
            "type": 1,
            "start_time": "2020-06-10T06:00:00Z",
            "duration": 120,
            "timezone": "Planet/Earth",
            "created_at": "2020-06-09T05:46:28Z",
            "join_url": "https://dummy.com/meetings/mydummy_2",
        }
    ]
    dummy_past_meetings_data = {
        "uuid": "dummy_uuid_1",
        "id": 1231231123,
        "host_id": "dummy_id_1",
        "type": 1,
        "topic": "its dummy meeting2",
        "user_name": "dummy username 1",
        "user_email": "dummy@dumb.com",
        "start_time": "2020-06-10T06:00:00Z",
        "end_time": "2020-05-12T06:20:41Z",
        "duration": 120,
        "total_minutes": 222,
        "participants_count": 231,
        "dept": "",
        "source": "Dummy institute",
    }
    expected_response = [
        {
            "type": "past_meetings",
            "parent_id": "1231231123",
            "created_at": "2020-06-10T06:00:00Z",
            "id": "dummy_uuid_1",
            "title": "its dummy meeting2",
            "body": "Meeting Duration:120\nMeeting Type:An instant meeting\nMeeting Participants : [{'id': 'dummy_id_1', 'name': 'dummy username 1', 'join_time': '2020-06-10T06:00:00Z', 'leave_time': '2020-05-12T06:20:41Z', 'duration': 120}]",
            "url": "https://zoom.us/user/dummy_id_1/meeting/1231231123",
            "_allow_permissions": ["User:Read", "ent_dummy_id_1", "ent_dummy_id_1_2"],
        }
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    dummy_past_meetings_data = json.dumps(dummy_past_meetings_data)
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = dummy_past_meetings_data
    mock_response[1].status_code = 404
    mock_request_get.side_effect = mock_response
    response = past_meetings_object.get_past_meetings_details_documents(
        dummy_meetings_data,
        SCHEMA,
        start_time,
        end_time,
        enable_permission,
    )
    assert response["type"] == PAST_MEETINGS
    assert response["data"] == expected_response
