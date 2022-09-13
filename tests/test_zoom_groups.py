#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys
import time

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.configuration import Configuration
from ees_zoom.constant import GROUPS
from ees_zoom.zoom_client import ZoomClient
from ees_zoom.zoom_groups import ZoomGroups

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)
SCHEMA = {
    "id": "id",
    "title": "name",
}


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    logger = logging.getLogger("unit_test_groups")
    return configuration, logger


def create_zoom_groups_object():
    """This function creates zoom_groups object for test."""
    configs, logger = settings()
    zoom_client = ZoomClient(configs, logger)
    zoom_client.access_token = "dummy"
    zoom_client.access_token_expiration = time.time() + 4000
    return ZoomGroups(configs, logger, zoom_client)


@pytest.mark.parametrize(
    "groups_list, groups_details_response_data",
    [
        (
            {
                "total_records": 1,
                "groups": [
                    {
                        "id": "dummy_group_id1",
                        "name": "Developers",
                        "total_members": 0,
                    }
                ],
            },
            [
                {
                    "type": "groups",
                    "id": "dummy_group_id1",
                    "title": "Developers",
                    "body": "total_members: 0",
                    "url": "https://zoom.us/account/group#/detail/dummy_group_id1/detail",
                }
            ],
        )
    ],
)
def test_get_groups_details(requests_mock, groups_list, groups_details_response_data):
    """Test that delete objects from Enterprise Search.
    :param requests_mock: fixture for mocking requests calls.
    :param groups_list: list of groups data.
    :param groups_details_response_data: document generated for fetched groups.
    """
    groups_object = create_zoom_groups_object()
    headers = {
        "authorization": "Bearer token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://api.zoom.us/v2/groups",
        headers=headers,
        json=groups_list,
        status_code=200,
    )
    groups_object.set_groups_list()
    response = groups_object.get_groups_details_documents(
        SCHEMA,
        groups_object.groups_list,
        False,
    )
    assert response["type"] == GROUPS
    assert response["data"] == groups_details_response_data
