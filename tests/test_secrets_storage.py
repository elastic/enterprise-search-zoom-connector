#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import json
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.secrets_storage import SecretsStorage  # noqa

SECRETS_JSON_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "ees_zoom",
    "secrets.json",
)

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_secrets_storage")
    return configuration, logger


def test_get_refresh_token_when_json_file_absent():
    """test the fetching mechanism of refresh token when secrets storage is unavailable."""
    config, logger = settings()
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    secrets_storage = SecretsStorage(config, logger)
    actual_refresh_token = secrets_storage.get_refresh_token()
    assert actual_refresh_token is None


def test_set_refresh_token_with_json_absent():
    """test the storing mechanism of refresh token when secrets storage is not available."""
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    dummy_refresh_token = "abcabcabcABCABCABC"
    secrets_storage.set_refresh_token(dummy_refresh_token)
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data["zoom.refresh_token"] == dummy_refresh_token


def test_set_refresh_token_with_json_present():
    """test the storing mechanism of refresh token when secrets storage is available."""
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    dummy_refresh_token = "abcabcabcABCABCABC"
    secrets_storage.set_refresh_token(dummy_refresh_token)
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data["zoom.refresh_token"] == dummy_refresh_token


def test_get_refresh_token_from_json_file():
    """test the fetching mechanism of refresh token when secrets storage is available."""
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    actual_refresh_token = secrets_storage.get_refresh_token()
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data["zoom.refresh_token"] == actual_refresh_token
