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
from ees_zoom.zoom_recordings import ZoomRecordings  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
RECORDING = "recordings"
SCHEMA = {
    "created_at": "recording_start",
    "id": "id",
    "size": "total_size",
    "title": "topic",
    "url": "play_url",
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
    logger = logging.getLogger("unit_test_recording")
    return configuration, logger, zoom_enterprise_search_mappings


def create_recordings_object():
    """This function create ZoomRecordings object for test.
    :returns ZoomRecordings: Instance of ZoomRecordings.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomRecordings(configs, logger, zoom_client, zoom_enterprise_search_mappings)


@mock.patch("requests.get")
def test_get_recordings_details_documents_positive(mock_request_get):
    """Test for generating recording documents, generated from data fetched from Zoom.
    :param mock_request_get: mock patch for requests.get calls.
    """
    recordings_object = create_recordings_object()
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
        "from": "2022-03-13",
        "to": "2022-04-13",
        "page_count": 1,
        "page_size": 30,
        "total_records": 4,
        "next_page_token": "dummy_next_page_token",
        "meetings": [
            {
                "uuid": "dummy_uuid",
                "id": 123123123,
                "account_id": "dummy_account_id",
                "host_id": "dummy_id_1",
                "topic": "Dummy meeting Topic",
                "type": 4,
                "start_time": "2022-03-22T05:53:05Z",
                "timezone": "Planet/Earth",
                "duration": 100,
                "total_size": 4002224,
                "recording_count": 3,
                "share_url": "https://dummy.share.url/dummy_uuid",
                "recording_files": [
                    {
                        "id": "dummy_uuid_dummy_recording_id1",
                        "meeting_id": "dummy_uuid",
                        "recording_start": "2022-03-22T05:53:15Z",
                        "recording_end": "2022-03-22T05:55:12Z",
                        "file_type": "M4A",
                        "file_extension": "M4A",
                        "file_size": 1856448,
                        "play_url": "https://dummy.play.url/dummy_recording_id1",
                        "download_url": "https://dummy.download.url/dummy_recording_id1",
                        "status": "completed",
                        "recording_type": "audio_only",
                    },
                    {
                        "id": "dummy_uuid_dummy_recording_id2",
                        "meeting_id": "dummy_uuid",
                        "recording_start": "2022-03-22T05:53:15Z",
                        "recording_end": "2022-03-22T05:55:12Z",
                        "file_type": "TIMELINE",
                        "file_extension": "JSON",
                        "file_size": 544,
                        "download_url": "https://dummy.download.url/dummy_recording_id2",
                        "status": "completed",
                        "recording_type": "timeline",
                    },
                    {
                        "id": "dummy_uuid_dummy_recording_id3",
                        "meeting_id": "dummy_uuid",
                        "recording_start": "2022-03-22T05:53:15Z",
                        "recording_end": "2022-03-22T05:55:12Z",
                        "file_type": "MP4",
                        "file_extension": "MP4",
                        "file_size": 2145232,
                        "play_url": "https://dummy.play.url/dummy_recording_id3",
                        "download_url": "https://dummy.download.url/dummy_recording_id3",
                        "status": "completed",
                        "recording_type": "shared_screen_with_speaker_view",
                    },
                ],
            },
        ],
    }
    mock_resp_without_next_page_token = {
        "from": "2022-03-13",
        "to": "2022-04-13",
        "page_count": 1,
        "page_size": 30,
        "total_records": 4,
        "next_page_token": "",
        "meetings": [
            {
                "uuid": "dummy_uuid2",
                "id": 908908908,
                "account_id": "dummy_account_id",
                "host_id": "dummy_id_1",
                "topic": "Dummy meeting Topic 2",
                "type": 4,
                "start_time": "2022-03-23T05:53:05Z",
                "timezone": "Planet/Earth",
                "duration": 100,
                "total_size": 1233321,
                "recording_count": 2,
                "share_url": "https://dummy.meeting2.share.url/dummy_uuid",
                "recording_files": [
                    {
                        "id": "dummy_uuid2_dummy_recording_id1",
                        "meeting_id": "dummy_uuid",
                        "recording_start": "2022-03-23T05:53:15Z",
                        "recording_end": "2022-03-23T05:55:12Z",
                        "file_type": "M4A",
                        "file_extension": "M4A",
                        "file_size": 1856448,
                        "play_url": "https://dummy.meeting2.play.url/dummy_recording_id1",
                        "download_url": "https://dummy.meeting2.download.url/dummy_recording_id1",
                        "status": "completed",
                        "recording_type": "audio_only",
                    },
                    {
                        "id": "dummy_uuid2_dummy_recording_id2",
                        "meeting_id": "dummy_uuid",
                        "recording_start": "2022-03-23T05:53:15Z",
                        "recording_end": "2022-03-23T05:55:12Z",
                        "file_type": "TIMELINE",
                        "file_extension": "JSON",
                        "file_size": 454,
                        "download_url": "https://dummy.meeting2.download.url/dummy_recording_id2",
                        "status": "completed",
                        "recording_type": "timeline",
                    },
                ],
            },
        ],
    }
    expected_response = [
        {
            "type": "recordings",
            "parent_id": "dummy_id_1",
            "created_at": "2022-03-22T05:53:15Z",
            "id": "dummy_uuid_dummy_recording_id1",
            "size": 4002224,
            "title": "Dummy meeting Topic",
            "url": "https://zoom.us/recording/management/detail?meeting_id=dummy_uuid",
            "body": "File MetaData\n File Type : M4A\n File Size : 1856448\n Recording Type : audio_only",
            "_allow_permissions": [
                "Recording:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "recordings",
            "parent_id": "dummy_id_1",
            "created_at": "2022-03-22T05:53:15Z",
            "id": "dummy_uuid_dummy_recording_id2",
            "size": 4002224,
            "title": "Dummy meeting Topic",
            "body": "File MetaData\n File Type : TIMELINE\n File Size : 544\n Recording Type : timeline",
            "url": "https://zoom.us/recording/management/detail?meeting_id=dummy_uuid",
            "_allow_permissions": [
                "Recording:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "recordings",
            "parent_id": "dummy_id_1",
            "created_at": "2022-03-22T05:53:15Z",
            "id": "dummy_uuid_dummy_recording_id3",
            "size": 4002224,
            "title": "Dummy meeting Topic",
            "url": "https://zoom.us/recording/management/detail?meeting_id=dummy_uuid",
            "body": "File MetaData\n File Type : MP4\n File Size : 2145232\n Recording Type : shared_screen_with_speaker_view",
            "_allow_permissions": [
                "Recording:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "recordings",
            "parent_id": "dummy_id_1",
            "created_at": "2022-03-23T05:53:15Z",
            "id": "dummy_uuid2_dummy_recording_id1",
            "size": 1233321,
            "title": "Dummy meeting Topic 2",
            "url": "https://zoom.us/recording/management/detail?meeting_id=dummy_uuid2",
            "body": "File MetaData\n File Type : M4A\n File Size : 1856448\n Recording Type : audio_only",
            "_allow_permissions": [
                "Recording:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
        {
            "type": "recordings",
            "parent_id": "dummy_id_1",
            "created_at": "2022-03-23T05:53:15Z",
            "id": "dummy_uuid2_dummy_recording_id2",
            "size": 1233321,
            "title": "Dummy meeting Topic 2",
            "body": "File MetaData\n File Type : TIMELINE\n File Size : 454\n Recording Type : timeline",
            "url": "https://zoom.us/recording/management/detail?meeting_id=dummy_uuid2",
            "_allow_permissions": [
                "Recording:Read",
                "ent_dummy_id_1",
                "ent_dummy_id_1_2",
            ],
        },
    ]
    start_time = datetime.datetime.strptime(
        "2020-05-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    end_time = datetime.datetime.strptime(
        "2020-06-11T06:20:41Z", RFC_3339_DATETIME_FORMAT
    )
    enable_permission = True
    mock_resp_with_next_page_token = json.dumps(mock_resp_with_next_page_token)
    mock_resp_without_next_page_token = json.dumps(mock_resp_without_next_page_token)
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = mock_resp_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = mock_resp_without_next_page_token
    mock_request_get.side_effect = mock_response
    response = recordings_object.get_recordings_details_documents(
        dummy_users_data,
        SCHEMA,
        start_time,
        end_time,
        enable_permission,
    )
    assert response["type"] == RECORDING
    assert response["data"] == expected_response


@mock.patch("requests.get")
def test_get_recordings_details_documents_negative(mock_request_get):
    """test case where Zoom is down
    :param mock_request_get: mock patch for requests.get calls.
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
    recordings_object = create_recordings_object()
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response.raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(BaseException):
        recordings_object.get_recordings_details_documents(
            dummy_users_data,
            SCHEMA,
            start_time,
            end_time,
            enable_permission,
        )
