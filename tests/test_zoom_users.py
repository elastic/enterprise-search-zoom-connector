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
from ees_zoom.utils import split_list_into_buckets

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest import mock  # noqa
from unittest.mock import Mock  # noqa

from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.constant import RFC_3339_DATETIME_FORMAT  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa
from ees_zoom.zoom_users import ZoomUsers  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
USERS = "users"
SCHEMA = {
    "created_at": "created_at",
    "id": "id",
    "title": "first_name",
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
    logger = logging.getLogger("unit_test_users")
    return configuration, logger, zoom_enterprise_search_mappings


def create_users_object():
    """This Method create ZoomUsers object for test.
    :returns ZoomUsers: Instance of ZoomUsers.
    """

    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomUsers(configs, logger, zoom_client, zoom_enterprise_search_mappings)


@mock.patch("requests.get")
def test_get_users_list_positive(mock_request_get):
    """Test Method to get all users from Zoom.
    :param mock_request_get: mock patch for requests.get calls."""
    users_object = create_users_object()
    mock_resp_with_next_page_token = {
        "page_count": 2,
        "page_number": 1,
        "page_size": 300,
        "total_records": 381,
        "next_page_token": "next_page_token",
        "users": [
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
                "created_at": "1111-11-11T11:11:11Z",
                "last_login_time": "2222-22-22T22:22:22Z",
                "last_client_version": "5.9.1.3506(mac)",
                "pic_url": "https://dummy_user_id1_url.com/",
                "language": "en-US",
                "phone_number": "",
                "status": "Passive",
                "role_id": "0",
            },
        ],
    }
    mock_resp_without_next_page_token = {
        "page_count": 2,
        "page_number": 1,
        "page_size": 300,
        "total_records": 381,
        "next_page_token": "",
        "users": [
            {
                "id": "dummy_id_2",
                "first_name": "user2",
                "last_name": "abc",
                "email": "dummy@dummy.com",
                "type": 2,
                "pmi": 198098098,
                "timezone": "Planet/Mars",
                "verified": 1,
                "dept": "",
                "created_at": "2222-22-22T22:22:22Z",
                "last_login_time": "3333-33-33T33:33:33Z",
                "last_client_version": "5.9.1.3506(mac)",
                "pic_url": "https://dummy_user_id2_url.com/",
                "language": "en-US",
                "phone_number": "",
                "status": "active",
                "role_id": "0",
            },
        ],
    }
    expected_response = [
        [
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
                "created_at": "1111-11-11T11:11:11Z",
                "last_login_time": "2222-22-22T22:22:22Z",
                "last_client_version": "5.9.1.3506(mac)",
                "pic_url": "https://dummy_user_id1_url.com/",
                "language": "en-US",
                "phone_number": "",
                "status": "Passive",
                "role_id": "0",
            }
        ],
        [
            {
                "id": "dummy_id_2",
                "first_name": "user2",
                "last_name": "abc",
                "email": "dummy@dummy.com",
                "type": 2,
                "pmi": 198098098,
                "timezone": "Planet/Mars",
                "verified": 1,
                "dept": "",
                "created_at": "2222-22-22T22:22:22Z",
                "last_login_time": "3333-33-33T33:33:33Z",
                "last_client_version": "5.9.1.3506(mac)",
                "pic_url": "https://dummy_user_id2_url.com/",
                "language": "en-US",
                "phone_number": "",
                "status": "active",
                "role_id": "0",
            }
        ],
    ]
    mock_resp_with_next_page_token = json.dumps(mock_resp_with_next_page_token)
    mock_resp_without_next_page_token = json.dumps(mock_resp_without_next_page_token)
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = mock_resp_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = mock_resp_without_next_page_token
    mock_request_get.side_effect = mock_response
    user_list = users_object.get_users_list()
    partitioned_users_list = split_list_into_buckets(
        user_list,
        users_object.config.get_value("zoom_sync_thread_count"),
    )
    assert partitioned_users_list == expected_response


def test_get_users_details_documents():
    """Test for getting all users documents generated using users_data."""
    users_data = [
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

    expected_response_data = [
        {
            "type": "users",
            "created_at": "2020-05-11T06:20:41Z",
            "id": "dummy_id_1",
            "title": "user1",
            "body": "First Name : user1\nLast Name : abc\nStatus : Passive\nRole Id : 0\nEmail : dummy@dummy.com",
            "url": "https://zoom.us/user/dummy_id_1/profile",
            "_allow_permissions": ["User:Read", "ent_dummy_id_1", "ent_dummy_id_1_2"],
        }
    ]
    enable_permission = True
    users_object = create_users_object()
    response = users_object.get_users_details_documents(
        SCHEMA,
        users_data,
        start_time,
        end_time,
        enable_permission,
    )
    assert response["type"] == USERS
    assert response["data"] == expected_response_data


@mock.patch("requests.get")
def test_get_users_list_negative(mock_request_get):
    """Test case where Zoom is down
    :param mock_request_get: mock patch for requests.get calls.
    """
    users_object = create_users_object()
    mock_response = [mock.Mock()]
    mock_response[0].status_code = 500
    mock_response[0].raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response[0].raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(Exception):
        assert users_object.get_users_list()
