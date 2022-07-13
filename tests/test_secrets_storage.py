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

REFRESH_TOKEN_FIELD = "zoom.refresh_token"
ACCESS_TOKEN_FIELD = "zoom.access_token"
EXPIRATION_TIME_FIELD = "zoom.access_token_expiry_time"


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_secrets_storage")
    return configuration, logger


def test_get_secrets_when_json_file_absent():
    """test the fetching mechanism of secret storage data when secrets storage is unavailable."""
    config, logger = settings()
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    secrets_storage = SecretsStorage(config, logger)
    secrets_storage = secrets_storage.get_secrets()
    assert secrets_storage is None


def test_set_secrets_with_json_absent():
    """test the storing mechanism of secret storage data when secrets storage is not available."""
    if os.path.exists(SECRETS_JSON_PATH):
        os.remove(SECRETS_JSON_PATH)
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    access_token_expiry_time = time.time() + 3500
    secrets = {
        REFRESH_TOKEN_FIELD: "xyzabcaaaabbbb",
        ACCESS_TOKEN_FIELD: "abcdfhghhshgg",
        EXPIRATION_TIME_FIELD: access_token_expiry_time,
    }
    secrets_storage.set_secrets(secrets)
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data["zoom.refresh_token"] == "xyzabcaaaabbbb" and secrets_data["zoom.access_token"] == "abcdfhghhshgg", secrets_data["zoom.access_token_expiry_time"] == access_token_expiry_time


def test_set_secrets_with_json_present():
    """test the storing mechanism of secret storage data when secrets storage is available."""
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    access_token_expiry_time = time.time() + 3500
    secrets = {
        REFRESH_TOKEN_FIELD: "xyzabcaaaabbbb",
        ACCESS_TOKEN_FIELD: "abcdfhghhshgg",
        EXPIRATION_TIME_FIELD: access_token_expiry_time,
    }
    secrets_storage.set_secrets(secrets)
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data["zoom.refresh_token"] == "xyzabcaaaabbbb" and secrets_data["zoom.access_token"] == "abcdfhghhshgg", secrets_data["zoom.access_token_expiry_time"] == access_token_expiry_time


def test_get_secrets_from_json_file():
    """test the fetching mechanism of secret storage data when secrets storage is available."""
    config, logger = settings()
    secrets_storage = SecretsStorage(config, logger)
    secrets_storage_data = secrets_storage.get_secrets()
    with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
        secrets_data = json.load(secrets_store)
    assert secrets_data == secrets_storage_data
