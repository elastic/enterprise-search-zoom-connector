#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import json
import os

SECRETS_JSON_PATH = os.path.join(os.path.dirname(__file__), "secrets.json")
REFRESH_TOKEN_FIELD = "zoom.refresh_token"


class SecretsStorage:
    """This Class handles the fetching and storing of refresh token to and from the secrets storage."""

    def __init__(self, config, logger) -> None:
        self.config = config
        self.logger = logger

    def get_refresh_token(self):
        """The module returns a dictionary containing refresh token, access token,and expiration time
        of access token(UTC format) from the secrets storage.
        :returns secret_store_data: a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) from the secrets storage.
        """
        if os.path.exists(SECRETS_JSON_PATH) and os.path.getsize(SECRETS_JSON_PATH) > 0:
            with open(SECRETS_JSON_PATH, encoding="UTF-8") as secrets_store:
                try:
                    secrets_store_data = json.load(secrets_store)
                    return secrets_store_data.get(REFRESH_TOKEN_FIELD)
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the secrets storage from path: {SECRETS_JSON_PATH}. Error: {exception}"
                    )

    def set_refresh_token(self, refresh_token):
        """The module stores a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) in to local secrets storage.
        :param secrets: a dictionary containing refresh token, access token and expiration time
        of access token(UTC format) to store in secrets storage.
        """
        secrets_store_data = {REFRESH_TOKEN_FIELD: refresh_token}
        with open(SECRETS_JSON_PATH, "w", encoding="UTF-8") as secrets_store:
            try:
                json.dump(secrets_store_data, secrets_store, indent=4)
                self.logger.info("Successfully saved the Refresh token in secrets")
            except Exception as exception:
                self.logger.exception(
                    f"Error while updating the secrets storage.\nError: {exception}"
                )
