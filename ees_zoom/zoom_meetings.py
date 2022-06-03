#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module will fetch meeting details for each user id present in
the list and will create documents from the fetched responses.
"""
import datetime
import json
import threading

import requests

from .constant import MEETINGS, RFC_3339_DATETIME_FORMAT
from .utils import retry


class ZoomMeetings:
    """Class is responsible to fetch all meetings and create documents for each.
    Store meetings in a list for use while indexing past-meetings.
    """

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.meetings_past_meetings_list = []
        self.retry_count = config.get_value("retry_count")

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def set_meetings_from_user_id(self, user_id, start_time, end_time):
        """Method will get all the Scheduled, upcoming, and live meetings for the
        passed user id and will return those meetings which falls in between start_time
        and end_time. It will add all meetings in class object for fetching past-meetings.
        :param user_id: string of the user ID.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :returns: List of valid meetings for user_id.
        """
        meetings_for_user = []
        next_page_token = True
        try:
            while next_page_token:
                url = f"https://api.zoom.us/v2/users/{user_id}/meetings?page_size=300"
                if next_page_token is not True:
                    url = f"{url}&next_page_token={next_page_token}"
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                meetings_response = requests.get(url=url, headers=headers)
                if meetings_response and meetings_response.status_code == 200:
                    response = json.loads(meetings_response.text)
                    next_page_token = response["next_page_token"]
                    meetings_for_user.extend(response[MEETINGS])
                elif meetings_response.status_code == 401:
                    self.zoom_client.get_token()
                else:
                    meetings_response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"Exception raised while fetching meetings from Zoom: {exception}"
            )
            raise exception
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching meetings from Zoom: {exception}"
            )
            raise exception
        self.meetings_past_meetings_list.extend(meetings_for_user)
        meetings_list = []
        for meeting in meetings_for_user:
            meeting_date = datetime.datetime.strptime(
                meeting["created_at"], RFC_3339_DATETIME_FORMAT
            )
            if meeting_date >= start_time and meeting_date <= end_time:
                meetings_list.append(meeting)
        self.logger.info(
            f"Thread: [{threading.get_ident()}] Fetched total : {len(meetings_list)} "
            f"number(s) of meetings for {user_id}."
        )
        return meetings_list

    def get_meetings_details_documents(
        self,
        users_data,
        meetings_schema,
        start_time,
        end_time,
        is_meetings_in_objects,
        enable_permission,
    ):
        """This method will iterate over list of users and will get all valid meetings
        for the user. it will create a document from the returned data ready to be indexed.
        :param users_data: list of dictionaries where each dictionary contains details fetched for a user from Zoom
        :param meetings_schema: dictionary of fields to be indexed for meetings.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :param is_meetings_in_objects: boolean to check the status of meetings in objects.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            meeting_type_enum_to_name_mapping = {
                "1": "An instant meeting",
                "2": "A scheduled meeting",
                "3": "A recurring meeting with no fixed time",
                "8": "A recurring meeting with fixed time",
            }
            meetings_documents = []
            for user in users_data:
                meetings_list = self.set_meetings_from_user_id(
                    user["id"], start_time, end_time
                )
                if is_meetings_in_objects:
                    count = 0
                    for meeting in meetings_list:
                        meeting_document = {
                            "type": MEETINGS,
                            "parent_id": str(user["id"]),
                        }
                        for ws_field, zoom_fields in meetings_schema.items():
                            meeting_document[ws_field] = meeting[zoom_fields]
                        meeting_document["body"] = (
                            f"Meeting Host : {meeting['host_id']}\nMeeting Type : "
                            f"{meeting_type_enum_to_name_mapping[str(meeting['type'])]}"
                        )
                        meeting_document[
                            "url"
                        ] = f"https://zoom.us/user/{user['id']}/meeting/{meeting['id']}"
                        if enable_permission:
                            permission_list = ["User:Read"]
                            permission_list.extend(
                                self.zoom_enterprise_search_mappings.get(user["id"], [])
                            )
                            meeting_document["_allow_permissions"] = permission_list
                        meetings_documents.append(meeting_document)
                        count += 1
                    self.logger.info(
                        f" Thread: [{threading.get_ident()}] {count} number(s) of Meetings Document generated."
                    )
            return {"type": MEETINGS, "data": meetings_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating meetings documents."
            )
            raise key_error_exception
        except Exception as exception:
            self.logger.error(
                f"Error while preparing Documents for meetings: {exception}"
            )
            raise exception
