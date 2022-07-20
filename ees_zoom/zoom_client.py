#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""zoom_client modules allows to generate access token for Zoom Oauth app,
with this access token is useful for running various Zoom APIs."""
import base64
import json
import threading
import time

import requests
import requests.exceptions

from .secrets_storage import SecretsStorage
from .utils import retry

ZOOM_AUTH_BASE_URL = "https://zoom.us/oauth/token?grant_type="
ZOOM_BASE_URL = "https://api.zoom.us/v2/"
REFRESH_TOKEN_FIELD = "zoom.refresh_token"
ACCESS_TOKEN_FIELD = "zoom.access_token"
EXPIRATION_TIME_FIELD = "zoom.access_token_expiry_time"


class AccessTokenGenerationException(Exception):
    """This class is used to generate the custom error exception when retry_count limit is exceeded."""

    def __init__(self, errors):
        super().__init__(
            f"Error while generating the Zoom access token. \nReason: {errors}"
        )
        self.errors = errors


lock = threading.Lock()


class ZoomClient:
    """This class is used to generate the access token to call different Zoom Apis."""

    def __init__(self, config, logger):
        self.retry_count = int(config.get_value("retry_count"))
        self.client_id = config.get_value("zoom.client_id")
        self.client_secret = config.get_value("zoom.client_secret")
        self.authorization_code = config.get_value("zoom.authorization_code")
        self.redirect_uri = config.get_value("zoom.redirect_uri")
        self.secrets_storage = SecretsStorage(config, logger)
        self.logger = logger
        self.config_file_path = config.file_name
        self.access_token_expiration = time.time()
        self.is_token_generated = False

    def get_headers(self):
        """generates header to fetch refresh token from zoom.

        Returns:
            request_headers: header to be used for requesting refresh token from Zoom.
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        credentials_bytes = credentials.encode("ascii")
        base64_bytes = base64.b64encode(credentials_bytes)
        base64_credentials = base64_bytes.decode("ascii")
        request_headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Authorization": f"Basic {base64_credentials}",
        }
        return request_headers

    def handle_4xx_error(self, json_data, http_error):
        """Module handles 4xx error ocurred while fetching tokens from Zoom.
        Raises the Exception accordingly.
        :param json_data: json response from Zoom.
        :param http_error: Exception raised from requests module.

        Raises:
            AccessTokenGenerationException: Custom Exception for handling 4xx error.
        """
        invalid_field = ""
        reason = json_data.get("reason", "")
        if reason in ["Invalid Token!", "Invalid authorization code"]:
            if not self.is_token_generated:
                self.is_token_generated = True
                # sleep to wait for secret storage update process while running cronjob with multiple syncs.
                time.sleep(1)
                lock.release()
                self.ensure_token_valid()
                return
            invalid_field = "zoom.authorization_code"
            secrets = {
                REFRESH_TOKEN_FIELD: "",
                ACCESS_TOKEN_FIELD: "",
                EXPIRATION_TIME_FIELD: "",
            }
            self.secrets_storage.set_secrets(secrets)
        elif reason == "Invalid request : Redirect URI mismatch.":
            invalid_field = "zoom.redirect_uri"
        else:
            invalid_field = "zoom.client_id or zoom.client_secret"

        raise AccessTokenGenerationException(
            f"HTTPError\n"
            f"Error: {http_error}\n"
            f"Reason: {reason}\n"
            f"Solution: Please update the {invalid_field} in zoom_connector.yml."
        )

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        )
    )
    def ensure_token_valid(self):
        """This module generates access token and refresh token using stored refresh token.
        If refresh token is not stored then uses authorization code."""
        lock.acquire()
        secrets = self.secrets_storage.get_secrets()
        refresh_token = ""

        if secrets:
            self.access_token_expiration = secrets.get(EXPIRATION_TIME_FIELD, "")
            refresh_token = secrets.get(REFRESH_TOKEN_FIELD, "")

        if self.access_token_expiration and time.time() < self.access_token_expiration:
            self.is_token_generated = False
            self.access_token = secrets.get(ACCESS_TOKEN_FIELD, "")
            lock.release()
            return

        self.logger.info(
            f"Generating the access token and updating refresh token for the client ID: {self.client_id}..."
        )

        if refresh_token and len(refresh_token):
            url = f"{ZOOM_AUTH_BASE_URL}refresh_token&refresh_token={refresh_token}"
        else:
            url = f"{ZOOM_AUTH_BASE_URL}authorization_code&code={self.authorization_code}&redirect_uri={self.redirect_uri}"
        try:
            response = requests.post(
                url=url,
                headers=self.get_headers(),
            )
            json_data = json.loads(response.text)
            response.raise_for_status()
            if response and response.status_code == requests.codes.ok:
                refresh_token = json_data["refresh_token"]
                self.access_token = json_data["access_token"]
                self.access_token_expiration = time.time() + 3500
                secrets = {
                    REFRESH_TOKEN_FIELD: refresh_token,
                    ACCESS_TOKEN_FIELD: self.access_token,
                    EXPIRATION_TIME_FIELD: self.access_token_expiration,
                }
                self.secrets_storage.set_secrets(secrets)
        except requests.exceptions.HTTPError as http_error:
            if response.status_code in [400, 401]:
                self.handle_4xx_error(json_data, http_error)
            self.logger.exception(f"HTTPError: {http_error}")
            raise http_error
        finally:
            if lock.locked():
                lock.release()

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def get(self, end_point, key, is_paginated=False):
        """Makes get call to Zoom api endpoint

        :param end_point: endpoint url with query parameters
        :param key: Response json key to parse on successful get call
        :returns api_response: list of dictionary containing response from endpoint.
        """
        # Set access token either from secrets storage or fetch new one from Zoom in case it is expired
        self.ensure_token_valid()
        next_page_token = True
        api_response = []

        try:
            while next_page_token:
                url = f"{ZOOM_BASE_URL}{end_point}"
                if next_page_token is not True:
                    url = f"{url}&next_page_token={next_page_token}"
                headers = {
                    "authorization": f"Bearer {self.access_token}",
                    "content-type": "application/json",
                }

                response = requests.get(url=url, headers=headers)

                if response and response.status_code == 200:
                    response = json.loads(response.text)
                    if key == "past_meetings":
                        return response
                    if response.get(key):
                        api_response.extend(response[key])
                    next_page_token = (
                        response.get("next_page_token") if is_paginated else None
                    )
                # Getting error code 400 but the zoom api documentation is suggesting error code 300
                elif key == "privileges" and response.status_code in [300, 400]:
                    raise requests.exceptions.HTTPError(response=response)
                elif response.status_code == 401:
                    self.ensure_token_valid()
                else:
                    response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"HTTP Error occurred while fetching response for {end_point} "
                f"from Zoom. Error: {exception}"
            )
            raise exception
        except Exception as exception:
            raise exception
        return api_response
