#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import json
import os

SECRETS_JSON_PATH = os.path.join(os.path.dirname(__file__), "secrets.json")
REFRESH_TOKEN_FIELD = "zoom.refresh_token"
ACCESS_TOKEN_FIELD = "zoom.access_token"
EXPIRATION_TIME_FIELD = "zoom.access_token_expiry_time"


class SecretsStorage:
    """This Class handles the fetching and storing of refresh token to and from the secrets storage."""

    def __init__(self, config, logger) -> None:
        self.config = config
        self.logger = logger

    def get_secrets(self):
        """The module returns a dictionary containing refresh token, access token,and expiration time
        of access token(UTC format) from the secrets storage.
        :returns secret_store_data: a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) from the secrets storage.
        """
        if os.path.exists(SECRETS_JSON_PATH) and os.path.getsize(SECRETS_JSON_PATH) > 0:
            with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
                try:
                    secrets = json.load(secrets_store)
                    return secrets
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the secrets storage from path: {SECRETS_JSON_PATH}. Error: {exception}"
                    )

    def set_secrets(self, secrets):
        """The module stores a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) in to local secrets storage.
        :param secrets: a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) to store in secrets storage.
        """
        with open(SECRETS_JSON_PATH, "w", encoding="UTF-8") as secrets_store:
            try:
                json.dump(secrets, secrets_store, indent=4)
                self.logger.info("Successfully saved the Refresh token in secrets")
            except Exception as exception:
                self.logger.exception(
                    f"Error while updating the secrets storage.\nError: {exception}"
                )
