#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module will fetch recordings for the user id present in
the list and will create a document from the fetched response.
"""
import json
import threading
import time

import requests

from .constant import MEETINGS, RFC_3339_DATETIME_FORMAT
from .utils import retry, url_encode
from .zoom_client import ZoomClient

RECORDINGS = "recordings"


class ZoomRecordings:
    """This class is responsible for fetching recordings from Zoom and push document created for each recording
    into the queue.
    """

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
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
    def get_recordings_from_user_id(
        self,
        user_id,
        start_time,
        end_time,
    ):
        """This function fetches the recordings for the user id occurred within month.
        :param user_id: string of user id to fetch recordings.
        :param start_time: start_time for lower limit for data fetching.
        :param end_time: end_time for upper limit for data fetching.
        :returns: list of dictionary containing recorded data for each user.
        """
        recordings_for_user = []
        next_page_token = True
        try:
            while next_page_token:
                url = f"https://api.zoom.us/v2/users/{user_id}/recordings?page_size=300&from={start_time}&to={end_time}"
                if next_page_token is not True:
                    url = f"{url}&next_page_token={next_page_token}"
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                recordings_response = requests.get(url=url, headers=headers)
                if recordings_response and recordings_response.status_code == 200:
                    response = json.loads(recordings_response.text)
                    next_page_token = response["next_page_token"]
                    recordings_for_user.extend(response[MEETINGS])
                elif recordings_response.status_code == 401:
                    if time.time() > self.zoom_client.access_token_expiration:
                        self.zoom_client.get_token()
                else:
                    recordings_response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"Exception raised while fetching recordings from Zoom: {exception}"
            )
            raise exception
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching recordings from Zoom: {exception}"
            )
            raise exception
        self.logger.info(
            f"Thread: [{threading.get_ident()}] fetched total : {len(recordings_for_user)} Recordings for {user_id}."
        )
        return recordings_for_user

    def get_recordings_details_documents(
        self,
        users_data,
        recordings_schema,
        start_time,
        end_time,
        enable_permission,
    ):
        """This method will iterate over list of users and will get all valid recording objects for the
        active meeting ids. it will create a document from the returned data ready to be indexed.
        :param users_data: list of dictionaries where each dictionary contains details fetched for a user from Zoom.
        :param recordings_schema: dictionary of fields to be indexed for meetings.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            recording_documents = []
            # common_param will be common for all the recordings of one meeting.
            common_param = [
                "host_id",
                "topic",
                "type",
                "share_url",
                "total_size",
                "duration",
            ]
            for user in users_data:
                self.logger.info(
                    f"Attempting to extract recordings for user {user['id']}."
                )
                recordings_list = self.get_recordings_from_user_id(
                    user["id"],
                    start_time.strftime(RFC_3339_DATETIME_FORMAT),
                    end_time.strftime(RFC_3339_DATETIME_FORMAT),
                )
                for meeting in recordings_list:
                    for recording in meeting["recording_files"]:
                        # skipping the recordings which are still in progress.
                        # skipped recordings will be indexed in the next execution.
                        if recording["status"] != "completed":
                            continue
                        recording_document = {
                            "type": RECORDINGS,
                            "parent_id": user["id"],
                        }
                        for ws_field, zoom_fields in recordings_schema.items():
                            if (recording["file_type"].upper() == "TIMELINE") and (
                                ws_field == "url"
                            ):
                                continue
                            if zoom_fields in common_param:
                                recording_document[ws_field] = meeting[zoom_fields]
                                continue
                            recording_document[ws_field] = recording[zoom_fields]
                        recording_document["body"] = (
                            f"File MetaData\n File Type : {recording['file_type']}"
                            f"\n File Size : {recording['file_size']}\n Recording Type : {recording['recording_type']}"
                        )
                        url_encoded_uuid = url_encode(meeting["uuid"])
                        recording_document[
                            "url"
                        ] = f"https://zoom.us/recording/management/detail?meeting_id={url_encoded_uuid}"
                        if enable_permission:
                            permission_list = ["Recording:Read"]
                            permission_list.extend(
                                self.zoom_enterprise_search_mappings.get(user["id"], [])
                            )
                            recording_document["_allow_permissions"] = permission_list
                        recording_documents.append(recording_document)

            self.logger.info(
                f"Thread: [{threading.get_ident()}] {len(recording_documents)} number(s) of "
                "Recordings documents generated."
            )
            return {"type": RECORDINGS, "data": recording_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating recordings documents."
            )
            raise key_error_exception
        except Exception as exception:
            self.logger.error(
                f"Error {exception} occurred while generating recordings documents."
            )
            raise exception
