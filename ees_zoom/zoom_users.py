#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module will fetch users details for each user present in
the Zoom Server and will create documents from the fetched responses.
"""
import datetime
import json
import threading
import time

import requests

from .constant import RFC_3339_DATETIME_FORMAT, USERS
from .utils import retry
from .zoom_client import ZoomClient


class ZoomUsers:
    """This class is responsible to setup list of users and will put documents created for users in
    queue.
    """

    def __init__(
        self, config, logger, zoom_client, zoom_enterprise_search_mappings
    ) -> None:
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.retry_count = config.get_value("retry_count")

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    @ZoomClient.regenerate_token()
    def get_users_list(self):
        """The method will fetch all the available users from Zoom
        :returns users_list: list of total users fetched from Zoom
        """
        users_list = []
        next_page_token = True
        try:
            while next_page_token:
                url = "https://api.zoom.us/v2/users?page_size=300"
                if next_page_token is not True:
                    url = f"{url}&next_page_token={next_page_token}"
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                users_response = requests.get(url=url, headers=headers)
                if users_response and users_response.status_code == 200:
                    response = json.loads(users_response.text)
                    next_page_token = response["next_page_token"]
                    users_list.extend(response[USERS])
                elif users_response.status_code == 401:
                    if time.time() > self.zoom_client.access_token_expiration:
                        self.zoom_client.get_token()
                else:
                    users_response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"Exception raised while fetching users from Zoom: {exception}"
            )
            raise exception
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching users from Zoom. : {exception}"
            )
            raise exception
        return users_list

    def get_users_details_documents(
        self,
        users_schema,
        users_data,
        start_time,
        end_time,
        enable_permission,
    ):
        """This method will create documents for users to be indexed in workplace search.
        :param users_schema: dictionary of fields available in schema.
        :param users_data: list of dictionaries where each dictionary contains details fetched for a user from Zoom.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: Dictionary containing type of data along with the data.
        """
        try:
            count = 0
            user_documents = []
            for user in users_data:
                user_created_at = datetime.datetime.strptime(
                    user["created_at"], RFC_3339_DATETIME_FORMAT
                )
                if user_created_at >= start_time and user_created_at <= end_time:
                    user_document = {"type": USERS}
                    for ws_field, zoom_fields in users_schema.items():
                        user_document[ws_field] = user[zoom_fields]
                    user_document["body"] = (
                        f"First Name : {user['first_name']}\nLast Name : {user['last_name']}\n"
                        f"Status : {user['status']}\n"
                        f"Role Id : {user['role_id']}\nEmail : {user['email']}"
                    )
                    user_document["url"] = f"https://zoom.us/user/{user['id']}/profile"
                    if enable_permission:
                        permission_list = ["User:Read"]
                        permission_list.extend(
                            self.zoom_enterprise_search_mappings.get(user["id"], [])
                        )
                        user_document["_allow_permissions"] = permission_list
                    user_documents.append(user_document)
                    count += 1
            self.logger.info(
                f"Thread: [{threading.get_ident()}] {count} number(s) of Users documents generated."
            )
            return {"type": USERS, "data": user_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating users documents."
            )
            raise key_error_exception
