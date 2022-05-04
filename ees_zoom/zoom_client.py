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

from .utils import retry, update_yml


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
        self.refresh_token = config.get_value("zoom.refresh_token")
        self.logger = logger
        self.config_file_path = config.file_name

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

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        )
    )
    def get_token(self):
        """Generates access token and stores the refresh token to call Zoom APIs"""
        self.logger.info(
            f"Generating the access token and updating refresh token for the client ID: {self.client_id}..."
        )
        invalid_field = ""
        try:
            url = f"""https://zoom.us/oauth/token?refresh_token={self.refresh_token}&grant_type=refresh_token"""
            response = requests.post(
                url=url,
                headers=self.get_headers(),
            )
            json_data = json.loads(response.text)
            response.raise_for_status()
            if response and response.status_code == requests.codes.ok:
                self.refresh_token = json_data["refresh_token"]
                self.access_token = json_data["access_token"]
                self.access_token_expiration = time.time() + 3500
                update_yml(
                    self.config_file_path, "zoom.refresh_token", self.refresh_token
                )
        except requests.exceptions.HTTPError as http_error:
            if response.status_code in [400, 401]:
                reason = json_data["reason"]
                if "reason" in json_data.keys() and reason == "Invalid Token!":
                    invalid_field = "zoom.refresh_token"
                else:
                    invalid_field = "zoom.client_id or zoom.client_secret"
                raise AccessTokenGenerationException(
                    f"HTTPError.\
                    Error: {http_error}\
                    Reason: {reason}\
                    Solution: Please update the {invalid_field} in zoom_connector.yml file.\
                    "
                )
            self.logger.exception(f"HTTPError: {http_error}")
            raise http_error
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as exception:
            raise exception
        except Exception as exception:
            raise AccessTokenGenerationException(exception)

    def regenerate_token():
        """Decorator for regenerating access_token after its expiraion time.
        calls the wrapped method to get new access_token from Zoom.
        """

        def decorator(func):
            """This function used as a decorator."""
            # the function that is used to check
            # the access token and refresh if necessary
            def wrapper(self, *args, **kwargs):
                """This function execute the refresh token logic if access token is expired."""
                lock.acquire()
                if time.time() > self.zoom_client.access_token_expiration:
                    self.zoom_client.get_token()
                lock.release()
                return func(self, *args, **kwargs)

            return wrapper

        return decorator
