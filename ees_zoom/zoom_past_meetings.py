#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module will fetch past_meetings details for each meeting id present in
the list and will create documents from the fetched responses.
"""
import datetime
import json
import threading

import requests

from .constant import PAST_MEETINGS, RFC_3339_DATETIME_FORMAT


class ZoomPastMeetings:
    """Class is responsible to fetch all past-meetings and create documents for each."""

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.retry_count = config.get_value("retry_count")

    def get_past_meeting_details_from_meeting_id(
        self, meeting_id, start_time, end_time
    ):
        """Method will get past_meeting instance for the passed meeting id and
        will return those meeting instances which falls in between start_time
        and end_time
        :param meeting_id: string of the meeting ID.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :returns: dictionary if meeting_id is past_meeting.
        """
        try:
            past_meeting_details = self.zoom_client.get(
                end_point=f"past_meetings/{meeting_id}", key=PAST_MEETINGS
            )
        except requests.exceptions.HTTPError as HTTPException:
            if HTTPException.__dict__["response"].status_code in [404, 400]:
                response = json.loads(HTTPException.__dict__["response"].text)
                self.logger.debug(
                    f"Meeting with id {meeting_id} is skipped. "
                    f"Error Code: {response['code']}, Reason: {response['message']}"
                )
                return None
            raise
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching past_meetings from Zoom. : {exception}"
            )
            raise exception
        meeting_date = datetime.datetime.strptime(
            past_meeting_details["end_time"], RFC_3339_DATETIME_FORMAT
        )
        if meeting_date >= start_time and meeting_date <= end_time:
            return past_meeting_details
        return None

    def get_meeting_participants(self, past_meeting_id):
        """Method will get all the participants who attended the meeting.
        :param past_meeting_id: Meeting id for which participants are fetched.
        :returns: List of valid meetings.
        """
        participants_for_meeting = []

        try:
            participants_for_meeting = self.zoom_client.get(
                end_point=f"report/meetings/{past_meeting_id}/participants?page_size=300",
                key="participants",
                is_paginated=True,
            )
        except requests.exceptions.HTTPError as HTTPException:
            if HTTPException.__dict__["response"].status_code != 404:
                self.logger.exception(
                    f"Unknown error occurred while fetching meeting participants from Zoom. Error: {HTTPException}"
                )
                raise
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching meeting participants from Zoom: {exception}"
            )
            raise exception
        self.logger.info(
            f"Thread: [{threading.get_ident()}] Fetched total : {len(participants_for_meeting)} "
            f"number(s) of meetings participants for {past_meeting_id}."
        )
        keys_to_index_from_participants_response = [
            "id",
            "name",
            "join_time",
            "leave_time",
            "duration",
        ]
        participants_details = []
        for participant in participants_for_meeting:
            participant_details = {
                key: val
                for key, val in participant.items()
                if key in keys_to_index_from_participants_response
            }
            participants_details.append(participant_details)
        return participants_details

    def get_past_meetings_details_documents(
        self,
        meetings_data,
        past_meetings_schema,
        start_time,
        end_time,
        enable_permission,
    ):
        """This Method will iterate over meetings list and will get all valid past_meetings
        for the meetingID. it will create a document from the returned data ready to be indexed.
        :param meetings_data: list of dictionaries where each dictionary contains details fetched for
        a meeting.
        :param past_meetings_schema: dictionary of fields to be indexed for past_meetings.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
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
            past_meetings_count = 0
            past_meetings_documents = []
            for meeting in meetings_data:
                past_meeting_dictionary = self.get_past_meeting_details_from_meeting_id(
                    str(meeting["id"]), start_time, end_time
                )
                if past_meeting_dictionary:
                    past_meeting_document = {
                        "type": PAST_MEETINGS,
                        "parent_id": str(meeting["id"]),
                    }
                    for ws_field, zoom_fields in past_meetings_schema.items():
                        past_meeting_document[ws_field] = past_meeting_dictionary[
                            zoom_fields
                        ]
                    participants_list = self.get_meeting_participants(meeting["id"])
                    if not len(participants_list):
                        # when meeting host is the only participant we will add it manually.
                        meeting_host_user_dictionary = {
                            "id": past_meeting_dictionary["host_id"],
                            "name": past_meeting_dictionary["user_name"],
                            "join_time": past_meeting_dictionary["start_time"],
                            "leave_time": past_meeting_dictionary["end_time"],
                            "duration": past_meeting_dictionary["duration"],
                        }
                        participants_list.append(meeting_host_user_dictionary)
                    past_meeting_document["body"] = (
                        f"Meeting Duration:{past_meeting_dictionary['duration']}\n"
                        f"Meeting Type:{meeting_type_enum_to_name_mapping[str(past_meeting_dictionary['type'])]}\n"
                        f"Meeting Participants : {participants_list}"
                    )
                    past_meeting_document[
                        "url"
                    ] = f"https://zoom.us/user/{meeting['host_id']}/meeting/{past_meeting_dictionary['id']}"
                    if enable_permission:
                        permission_list = ["User:Read"]
                        permission_list.extend(
                            self.zoom_enterprise_search_mappings.get(
                                meeting["host_id"], []
                            )
                        )
                        past_meeting_document["_allow_permissions"] = permission_list
                    past_meetings_documents.append(past_meeting_document)
                    past_meetings_count += 1
            self.logger.info(
                f"Thread: [{threading.get_ident()}] {past_meetings_count} number(s) of "
                f"Past_Meetings documents generated."
            )
            return {"type": PAST_MEETINGS, "data": past_meetings_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating past_meetings documents."
            )
            raise key_error_exception
        except Exception as exception:
            self.logger.error(
                f"Error occurred while preparing Documents for past_meetings: {exception}"
            )
            raise exception
