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

import requests
from dateutil.relativedelta import relativedelta

from .constant import FILES
from .utils import constraint_time_range, extract, retry

TIME_CONSTRAINT_FOR_CHATS = (datetime.utcnow()) + relativedelta(months=-6, days=+4)


class ZoomChatMessages:
    """This class will fetch files and chats for each user and will push created documents in the queue."""

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.retry_count = config.get_value("retry_count")

    def get_files_from_user_id(self, user_id, start_time, end_time):
        """This method will fetch all the files sent by the user, save it in the list.
        :param user_id: string of the user ID.
        :param start_time: datetime string for Lower limit for data fetching.
        :param end_time: datetime string for upper limit for data fetching.
        :returns: list of dictionary containing files of the user.
        """
        user_files = []
        try:
            url = (
                f"chat/users/{user_id}/messages?page_size=300&search_key=%20&"
                f"search_type=file&from={start_time}&to={end_time}"
            )
            user_files = self.zoom_client.get(
                end_point=url, key="messages", is_paginated=True
            )
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching file(s) from Zoom: {exception}"
            )
            raise
        return user_files

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def fetch_file_content(self, file_download_url):
        """This method will fetch the file content from file download url using
        get request from Zoom.
        :param file_download_url: file download url.
        :returns: file content.
        """
        attachment_content_response = None
        try:
            attachment_content_response = requests.get(file_download_url)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exception:
            self.logger.exception(
                f"Exception raised while fetching file content from Zoom: {exception}"
            )
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching file content from Zoom: {exception}"
            )
        return attachment_content_response

    def get_files_details_documents(
        self,
        users,
        files_schema,
        start_time,
        end_time,
        enable_permission,
    ):
        """This method will iterate over list of users and will get all the files sent by user,
        it will create files documents from the returned data ready to be indexed.
        :param users: list of dictionaries containing User details.
        :param files_schema: dictionary of fields to be indexed for Files.
        :param start_time: datetime object for lower limit for data fetching.
        :param end_time: datetime object for upper limit for data fetching.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            start_time, end_time = constraint_time_range(
                start_time=start_time, end_time=end_time, time_constraint=TIME_CONSTRAINT_FOR_CHATS, logger=self.logger
            )
            files_documents = []
            for user in users:
                self.logger.info(
                    f"Thread: [{threading.get_ident()}] Attempting to extract file(s) for user {user}."
                )
                file_list = self.get_files_from_user_id(user, start_time, end_time)
                self.logger.info(
                    f"Thread: [{threading.get_ident()}] Fetched total : {len(file_list)} file(s) for {user}."
                )
                for file in file_list:
                    # skipping the file if it's already fetched by any previous user id.
                    if any(
                        document["id"] == file["file_id"]
                        for document in files_documents
                    ):
                        continue
                    file_document = {"type": FILES, "parent_id": user}
                    for ws_field, zoom_fields in files_schema.items():
                        file_document[ws_field] = file[zoom_fields]
                    attachment_content_response = self.fetch_file_content(
                        file["download_url"]
                    )
                    content = ""
                    if attachment_content_response:
                        file_name = file.get("file_name", "file_id")
                        self.logger.info(f"Fetching Content of file : {file_name}")
                        content = extract(
                            attachment_content_response,
                            file_name,
                            self.logger,
                            retry_count=2,
                        )
                    file_document[
                        "body"
                    ] = f"Sender : {file['sender']}\nFile Content : {content}"
                    if enable_permission:
                        permission_list = ["ChatMessage:Read"]
                        permission_list.extend(
                            self.zoom_enterprise_search_mappings.get(user, [])
                        )
                        file_document["_allow_permissions"] = permission_list
                    files_documents.append(file_document)
            self.logger.info(
                f"Thread: [{threading.get_ident()}] Fetched total {len(files_documents)} file(s) documents."
            )
            return {"type": FILES, "data": files_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating file(s) documents."
            )
            raise
        except Exception as exception:
            self.logger.error(
                f"Error {exception} occurred while generating file(s) documents."
            )
            raise
