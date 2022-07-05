#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys
import time
from unittest import mock
from unittest.mock import MagicMock

import pytest
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.secrets_storage import SecretsStorage  # noqa
from ees_zoom.zoom_client import ZoomClient  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)

SECRETS_JSON_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "ees_zoom",
    "secrets.json",
)

AUTH_BASE_URL = "https://zoom.us/oauth/token?grant_type="
REFRESH_TOKEN_FIELD = "zoom.refresh_token"
ACCESS_TOKEN_FIELD = "zoom.access_token"
EXPIRATION_TIME_FIELD = "zoom.access_token_expiry_time"


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_zoom_client")
    return configuration, logger


def test_ensure_token_valid_when_valid_refresh_token_present(requests_mock):
    """Test for ensure_token_valid function call when valid refresh token is present in secrets storage.
    :param requests_mock: fixture for mocking requests calls.
    """
    new_refresh_token = "new_dummy_refresh_token"
    old_refresh_token = "old_dummy_refresh_token"
    access_token = "dummy_access_token"
    json_response = {"refresh_token": new_refresh_token, "access_token": access_token}
    config, logger = settings()
    zoom_client_object = ZoomClient(config, logger)
    secrets_storage = SecretsStorage(config, logger)
    access_token_expiry_time = time.time() - 3500
    secrets = {
        REFRESH_TOKEN_FIELD: old_refresh_token,
        ACCESS_TOKEN_FIELD: access_token,
        EXPIRATION_TIME_FIELD: access_token_expiry_time,
    }
    zoom_client_object.secrets_storage.get_secrets = MagicMock(return_value=secrets)
    url = f"{AUTH_BASE_URL}refresh_token&refresh_token={old_refresh_token}"
    headers = zoom_client_object.get_headers()
    requests_mock.post(
        url,
        headers=headers,
        json=json_response,
        status_code=200,
    )
    zoom_client_object.ensure_token_valid()
    assert zoom_client_object.access_token == access_token
    assert secrets_storage.get_secrets().get(REFRESH_TOKEN_FIELD) == new_refresh_token


@mock.patch("requests.get")
def test_ensure_token_valid_when_invalid_refresh_token_present(mock_request_get):
    """Test for ensure_token_valid function call when invalid refresh token is present in secrets storage.
    :param mock_request_get: mock patch for requests.get calls.
    """
    old_refresh_token = "old_dummy_refresh_token"
    access_token = "dummy_access_token"
    config, logger = settings()
    zoom_client_object = ZoomClient(config, logger)
    access_token_expiry_time = time.time() - 3500
    secrets = {
        REFRESH_TOKEN_FIELD: old_refresh_token,
        ACCESS_TOKEN_FIELD: access_token,
        EXPIRATION_TIME_FIELD: access_token_expiry_time,
    }
    zoom_client_object.secrets_storage.get_secrets = MagicMock(return_value=secrets)
    mock_response = [mock.Mock()]
    mock_response[0].status_code = 500
    mock_response[0].raise_for_status = mock.Mock()
    raise_for_status = requests.exceptions.HTTPError
    mock_response[0].raise_for_status.side_effect = raise_for_status
    mock_request_get.return_value = mock_response
    with pytest.raises(Exception):
        assert zoom_client_object.ensure_token_valid()


def test_ensure_token_valid_when_refresh_token_absent(requests_mock):
    """Test for ensure_token_valid function call when refresh token is not present in secrets storage.
    :param requests_mock: fixture for mocking requests calls.
    """
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    new_refresh_token = "new_dummy_refresh_token"
    access_token = "dummy_access_token"
    json_response = {"refresh_token": new_refresh_token, "access_token": access_token}
    config, logger = settings()
    zoom_client_object = ZoomClient(config, logger)
    secrets_storage = SecretsStorage(config, logger)
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
    zoom_client_object.ensure_token_valid()
    assert zoom_client_object.access_token == access_token
    assert secrets_storage.get_secrets().get(REFRESH_TOKEN_FIELD) == new_refresh_token
    assert secrets_storage.get_secrets().get(ACCESS_TOKEN_FIELD) == access_token
