#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""zoom_channels module is responsible to get all the available channels based on
user id from Zoom and generate documents from fetched responses."""

import threading

from .constant import CHANNELS


class ZoomChannels:
    """Class is responsible to fetch all channels and create documents for each."""

    def __init__(self, config, logger, zoom_client, zoom_enterprise_search_mappings):
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.retry_count = config.get_value("retry_count")

    def get_channels_from_user_id(self, user_id):
        """This function is used to fetch channels from Zoom based on user id.
        :param user_id: String of Zoom user id.
        :returns: list of dictionary containing channels.
        """
        channels_list = []
        try:
            channels_list = self.zoom_client.get(
                end_point=f"chat/users/{user_id}/channels?page_size=50",
                key=CHANNELS,
                is_paginated=True,
            )
        except Exception as exception:
            self.logger.exception(
                f"Unknown error occurred while fetching channels from Zoom: {exception}"
            )
            raise exception
        self.logger.info(
            f"Thread: [{threading.get_ident()}] Fetched total : {len(channels_list)} channels for {user_id}."
        )
        return channels_list

    def get_channels_details_documents(
        self,
        users_data,
        channel_schema,
        enable_permission,
    ):
        """This function will create channels documents to index in workplace search
        :param users_data: list of dictionaries where each dictionary contains details fetched for a user from Zoom.
        :param channel_schema: dictionary of fields available in include fields and DEFAULT_SCHEMA.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            channel_documents = []
            for user in users_data:
                channels_list = self.get_channels_from_user_id(user["id"])
                if len(channels_list) <= 0:
                    continue
                for channel in channels_list:
                    channels_dict = {"type": CHANNELS}
                    for ws_field, zoom_fields in channel_schema.items():
                        channels_dict[ws_field] = channel[zoom_fields]
                    channels_dict["body"] = f"{channel['channel_settings']}"
                    channels_dict[
                        "url"
                    ] = f"https://zoom.us/account/imchannel/old#/member/{channel['id']}"
                    if enable_permission:
                        permission_list = ["ChatChannel:Read"]
                        permission_list.extend(
                            self.zoom_enterprise_search_mappings.get(user["id"], [])
                        )
                        channels_dict["_allow_permissions"] = permission_list
                    channel_documents.append(channels_dict)
            self.logger.info(
                f"Thread: [{threading.get_ident()}] {len(channel_documents)} number(s) of Channels "
                f"documents generated."
            )
            return {"type": CHANNELS, "data": channel_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating channels documents."
            )
            raise key_error_exception
        except Exception as exception:
            self.logger.error(
                f"Error occurred while preparing document for channels : {exception}"
            )
            raise exception
