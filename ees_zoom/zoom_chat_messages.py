#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module will fetch chats and files details for each user id present in
the all_chat_access list and will create documents from the fetched responses.
"""
import threading
from datetime import datetime

from dateutil.relativedelta import relativedelta

from .constant import CHATS
from .utils import constraint_time_range

TIME_CONSTRAINT_FOR_CHATS = (datetime.utcnow()) + relativedelta(months=-6, days=+4)


class ZoomChatMessages:
    """This class will fetch files and chats for each user and will push created documents in the queue."""

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.retry_count = config.get_value("retry_count")

    def get_chats_from_user_id(self, user_id, start_time, end_time):
        """This method is responsible to fetch chats initiated by the user id, which are in range of past
        six months.
        :param user_id: String of Zoom user id.
        :param start_time: datetime string for lower limit for data fetching.
        :param end_time: datetime string for upper limit for data fetching.
        :returns: list of dictionary containing chats of the user.
        """
        user_chats = []
        try:
            url = (
                f"chat/users/{user_id}/messages?page_size=300&search_key=%20"
                f"&search_type=message&from={start_time}&to={end_time}"
            )
            user_chats = self.zoom_client.get(
                end_point=url, key="messages", is_paginated=True
            )
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching chats from Zoom: {exception}"
            )
            raise exception
        self.logger.info(
            f"Thread: [{threading.get_ident()}] Fetched total : {len(user_chats)} chat(s) for {user_id}."
        )
        return user_chats

    def get_chat_messages(
        self,
        users_data,
        chats_schema,
        start_time,
        end_time,
        enable_permission,
    ):
        """This method will iterate over list of users and will get all the chats of user,
        it will create chats documents from the returned data ready to be indexed.
        :param users_data: list of dictionaries where each dictionary contains details fetched for a user from Zoom.
        :param chats_schema: dictionary of fields to be indexed for Chats.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            chats_documents = []
            start_time, end_time = constraint_time_range(
                start_time=start_time, end_time=end_time, time_constraint=TIME_CONSTRAINT_FOR_CHATS, logger=self.logger
            )
            for user in users_data:
                self.logger.info(
                    f"Thread: [{threading.get_ident()}] Attempting to extract"
                    f" chat(s) of user {user}"
                )
                chats_list = self.get_chats_from_user_id(user, start_time, end_time)
                for chat in chats_list:
                    # skipping the chat if it's already fetched by any previous user id.
                    if any(
                        document["id"] == chat["id"] for document in chats_documents
                    ):
                        continue
                    chat_document = {"type": CHATS, "parent_id": user}
                    for ws_field, zoom_fields in chats_schema.items():
                        chat_document[ws_field] = chat[zoom_fields]
                    chat_document["body"] = f"Message : {chat['message']}"
                    chat_document[
                        "url"
                    ] = "https://zoom.us/account/archivemsg/search#/list"
                    if enable_permission:
                        permission_list = ["ChatMessage:Read"]
                        permission_list.extend(
                            self.zoom_enterprise_search_mappings.get(user, [])
                        )
                        chat_document["_allow_permissions"] = permission_list
                    chats_documents.append(chat_document)
            self.logger.info(
                f"Thread: [{threading.get_ident()}] Fetched total {len(chats_documents)} chat(s) documents."
            )
            return {"type": CHATS, "data": chats_documents}
        except Exception as exception:
            self.logger.error(
                f"Error {exception} occurred while generating chat(s) documents."
            )
            raise exception
