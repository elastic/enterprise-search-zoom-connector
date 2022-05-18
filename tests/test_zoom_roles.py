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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest import mock
from unittest.mock import Mock

from ees_zoom.configuration import Configuration
from ees_zoom.zoom_client import ZoomClient
from ees_zoom.zoom_roles import ZoomRoles

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
ROLES = "roles"
SCHEMA = {
    "description": "description",
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
    logger = logging.getLogger("unit_test_roles")
    return configuration, logger, zoom_enterprise_search_mappings


def create_roles_object():
    """This function create roles object for test.
    :returns ZoomRoles: Instance of ZoomRoles.
    """
    configs, logger, zoom_enterprise_search_mappings = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomRoles(configs, logger, zoom_client, zoom_enterprise_search_mappings)


def test_fetch_role_permissions(requests_mock):
    """Test for fetching roles_permissions from Zoom.
    :param requests_mock: fixture for requests.get calls.
    """
    dummy_roles_data = {
        "id": "dummy1",
        "name": "dummy",
        "description": "dummy roles description",
        "total_members": 111,
        "privileges": [
            "Prev1:dummy",
            "Prev2:dummy",
        ],
        "sub_account_privileges": {},
    }
    roles_object = create_roles_object()
    dummy_role_id = "dummy_role_1"
    headers = {
        "authorization": "Bearer token",
        "content-type": "application/json",
    }
    requests_mock.get(
        f"https://api.zoom.us/v2/roles/{dummy_role_id}",
        headers=headers,
        json=dummy_roles_data,
        status_code=200,
    )
    response = roles_object.fetch_role_permissions(dummy_role_id)
    assert response == dummy_roles_data["privileges"]


@mock.patch("requests.get")
def test_fetch_members_of_role(mock_request_get):
    """Test for fetching role members from Zoom.
    :param mock_request_get: mock patch for requests.get calls.
    """
    dummy_roles_members_data_with_next_page_token = {
        "page_count": 1,
        "page_number": 1,
        "next_page_token": "dummy_next_page_token",
        "page_size": 300,
        "total_records": 2,
        "members": [
            {
                "id": "dummy_user_id_1",
                "email": "dummy_@dumb.com",
                "first_name": "dummy_user",
                "last_name": "dummy_user_lastname",
                "type": 100,
                "department": "dummy",
            }
        ],
    }
    dummy_roles_members_data_without_next_page_token = {
        "page_count": 1,
        "page_number": 1,
        "next_page_token": "",
        "page_size": 300,
        "total_records": 1,
        "members": [
            {
                "id": "dummy_user_id_2",
                "email": "dummy_2@dumb.com",
                "first_name": "dummy_user2",
                "last_name": "dummy_user2_lastname",
                "type": 100,
                "department": "dummy",
            }
        ],
    }
    expected_roles_members_response = ["dummy_user_id_1", "dummy_user_id_2"]
    roles_object = create_roles_object()
    dummy_role_id = "dummy_role_1"
    dummy_roles_members_data_with_next_page_token = json.dumps(
        dummy_roles_members_data_with_next_page_token
    )
    dummy_roles_members_data_without_next_page_token = json.dumps(
        dummy_roles_members_data_without_next_page_token
    )
    mock_response = [Mock(), Mock()]
    mock_response[0].status_code = 200
    mock_response[0].text = dummy_roles_members_data_with_next_page_token
    mock_response[1].status_code = 200
    mock_response[1].text = dummy_roles_members_data_without_next_page_token
    mock_request_get.side_effect = mock_response
    response = roles_object.fetch_members_of_role(dummy_role_id)
    assert response == expected_roles_members_response
