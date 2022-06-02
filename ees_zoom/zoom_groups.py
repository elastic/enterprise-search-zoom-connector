#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

"""zoom_groups module is responsible to get all the available groups from Zoom."""

import json
import threading

import requests

from .constant import GROUPS
from .utils import retry


class ZoomGroups:
    """Class is responsible to fetch all groups available in Zoom, creates a list containing these groups and
    generates documents for each group fetched.
    """

    def __init__(self, config, logger, zoom_client):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.groups_list = []
        self.retry_count = config.get_value("retry_count")

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def set_groups_list(self):
        """This function will fetch all the available groups from zoom
        and will create a list of dictionary for groups data."""
        try:
            url = "https://api.zoom.us/v2/groups"
            headers = {
                "authorization": f"Bearer {self.zoom_client.access_token}",
                "content-type": "application/json",
            }
            groups_response = requests.get(url=url, headers=headers)
            if groups_response and groups_response.status_code == 200:
                response = json.loads(groups_response.text)
                self.groups_list.extend(response[GROUPS])
            elif groups_response.status_code == 401:
                self.zoom_client.get_token()
                self.set_groups_list()
            else:
                groups_response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"Exception raised while fetching groups from Zoom: {exception}"
            )
            raise exception
        except Exception as exception:
            self.logger.error(
                f"Error occurred while fetching groups from Zoom: {exception}"
            )

    def get_groups_details_documents(
        self,
        groups_schema,
        groups_data,
        enable_permission,
    ):
        """This function will create documents to index in workplace search
        :param groups_schema: dictionary of fields available in Include_fields and DEFAULT_SCHEMA.
        :param groups_data: list of dictionary contains groups data fetched from zoom api.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary of valid documents for groups object to be indexed.
        """
        try:
            if not groups_data:
                return {"type": GROUPS, "data": []}
            groups_count = 0
            groups_documents = []
            for group in groups_data:
                group_document = {"type": GROUPS}
                for ws_field, zoom_fields in groups_schema.items():
                    group_document[ws_field] = group[zoom_fields]
                group_document["body"] = f"total_members: {group['total_members']}"
                group_document[
                    "url"
                ] = f"https://zoom.us/account/group#/detail/{group['id']}/detail"
                if enable_permission:
                    group_document["_allow_permissions"] = ["Group:Read"]
                groups_documents.append(group_document)
                groups_count += 1
            self.logger.info(
                f"Thread: [{threading.get_ident()}] {groups_count} number(s) of Groups documents generated."
            )
            return {"type": GROUPS, "data": groups_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating groups documents."
            )
            raise key_error_exception
