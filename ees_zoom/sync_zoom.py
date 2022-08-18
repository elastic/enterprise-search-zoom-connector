#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""sync_zoom module allows to sync data to Elastic Enterprise Search.
It's possible to run full syncs and incremental syncs with this module."""
import threading

from .adapter import DEFAULT_SCHEMA
from .constant import (CHANNELS, CHATS, GROUPS, MEETINGS, PAST_MEETINGS,
                       RECORDINGS, ROLES, USERS)
from .utils import split_list_into_buckets
from .zoom_channels import ZoomChannels
from .zoom_groups import ZoomGroups
from .zoom_chat_messages import ZoomChatMessages
from .zoom_meetings import ZoomMeetings
from .zoom_past_meetings import ZoomPastMeetings
from .zoom_recordings import ZoomRecordings
from .zoom_roles import ZoomRoles
from .zoom_users import ZoomUsers

MULTITHREADED_OBJECTS_FOR_DELETION = "multithreaded_objects_for_deletion"


class SyncZoom:
    """This class allows ingesting data from Zoom to Elastic Enterprise Search."""

    def __init__(
        self,
        config,
        logger,
        workplace_search_client,
        zoom_client,
        objects_time_range,
        queue,
        zoom_enterprise_search_mappings,
    ):
        self.config = config
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.zoom_client = zoom_client
        self.objects_time_range = objects_time_range
        self.queue = queue
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.configuration_objects = config.get_value("objects")
        self.enable_permission = config.get_value("enable_document_permission")
        self.zoom_sync_thread_count = config.get_value("zoom_sync_thread_count")

    def get_schema_fields(self, document_name):
        """Returns the schema of all the include fields or exclude fields specified in the configuration file.
        :param document_name: Document name from users.
        Returns:
            schema: Included and excluded fields schema
        """
        fields = self.configuration_objects.get(document_name)
        adapter_schema = DEFAULT_SCHEMA[document_name]
        field_id = adapter_schema["id"]
        if fields:
            include_fields = fields.get("include_fields")
            exclude_fields = fields.get("exclude_fields")
            if include_fields:
                adapter_schema = {
                    key: val
                    for key, val in adapter_schema.items()
                    if val in include_fields
                }
            elif exclude_fields:
                adapter_schema = {
                    key: val
                    for key, val in adapter_schema.items()
                    if val not in exclude_fields
                }
            adapter_schema["id"] = field_id
        return adapter_schema

    def get_all_users_from_zoom(self):
        """Connects to the Zoom and returns the list of all the users from Zoom after
        partitioning them into equal buckets."""
        users_object = ZoomUsers(
            self.config,
            self.logger,
            self.zoom_client,
            self.zoom_enterprise_search_mappings,
        )
        partitioned_users_lists = split_list_into_buckets(
            documents=users_object.get_users_list(),
            total_buckets=self.zoom_sync_thread_count,
        )
        return partitioned_users_lists

    def fetch_users_and_append_to_queue(self, partitioned_users_list):
        """This method fetches the users from Zoom server and
        appends them to the shared queue
        :param partitioned_users_list: list of dictionaries where each dictionary contains details fetched for
        a user from Zoom
        :returns: list of users documents.
        """
        users_object = ZoomUsers(
            self.config,
            self.logger,
            self.zoom_client,
            self.zoom_enterprise_search_mappings,
        )
        users_schema = self.get_schema_fields(USERS)
        fetched_documents = users_object.get_users_details_documents(
            users_schema=users_schema,
            users_data=partitioned_users_list,
            start_time=self.objects_time_range[USERS][0],
            end_time=self.objects_time_range[USERS][1],
            enable_permission=self.enable_permission,
        )
        users_data = fetched_documents["data"]
        self.queue.append_to_queue(users_data)
        return users_data

    def get_meetings(
        self, partitioned_users_list, meetings_object, is_meetings_in_objects
    ):
        """This method fetches the meetings from Zoom server.
        :param partitioned_users_list: list of dictionaries where each dictionary contains details fetched for
        a user from Zoom
        :param meetings_object: ZoomMeetings Object.
        :param is_meetings_in_objects: boolean whether meetings object is in objects list.
        :returns: list of meetings documents.
        """
        if is_meetings_in_objects:
            checkpoint_object = MEETINGS
            meetings_schema = self.get_schema_fields(MEETINGS)
        else:
            checkpoint_object = PAST_MEETINGS
            meetings_schema = {}
        fetched_documents = meetings_object.get_meetings_details_documents(
            users_data=partitioned_users_list,
            meetings_schema=meetings_schema,
            start_time=self.objects_time_range[checkpoint_object][0],
            end_time=self.objects_time_range[checkpoint_object][1],
            is_meetings_in_objects=is_meetings_in_objects,
            enable_permission=self.enable_permission,
        )
        meetings_data = fetched_documents["data"]
        return meetings_data

    def get_past_meetings(self, meetings_object):
        """This method fetches the past-meetings from Zoom server.
        :param meetings_object: ZoomMeetings Object.
        :returns: list of past-meetings documents.
        """
        past_meetings_object = ZoomPastMeetings(
            self.config,
            self.logger,
            self.zoom_client,
            self.zoom_enterprise_search_mappings,
        )
        past_meetings_schema = self.get_schema_fields(PAST_MEETINGS)
        fetched_documents = []
        fetched_documents = past_meetings_object.get_past_meetings_details_documents(
            meetings_data=meetings_object.meetings_past_meetings_list,
            past_meetings_schema=past_meetings_schema,
            start_time=self.objects_time_range[PAST_MEETINGS][0],
            end_time=self.objects_time_range[PAST_MEETINGS][1],
            enable_permission=self.enable_permission,
        )
        past_meetings_data = fetched_documents["data"]
        return past_meetings_data

    def fetch_roles_and_append_to_queue(self, roles_object):
        """This method fetches the roles from Zoom server and
        appends them to the shared queue
        :param roles_object: ZoomRoles Object.
        :returns: list of roles documents.
        """
        roles_document_list = []
        roles_schema = self.get_schema_fields(ROLES)
        roles_object.set_list_of_roles_from_zoom()
        roles_list = split_list_into_buckets(
            roles_object.roles_list, self.zoom_sync_thread_count
        )
        for roles in roles_list:
            fetched_documents = roles_object.get_roles_details_documents(
                roles_schema=roles_schema,
                roles_data=roles,
                enable_permission=self.enable_permission,
            )
            roles_data = fetched_documents["data"]
            self.queue.append_to_queue(roles_data)
            roles_document_list.extend(roles_data)
        return roles_document_list

    def fetch_groups_and_append_to_queue(self, groups_object):
        """This method fetches the groups from Zoom server and
        appends them to the shared queue
        :param groups_object: ZoomGroups Object.
        :returns: list of groups documents.
        """
        groups_schema = self.get_schema_fields(GROUPS)
        groups_object.set_groups_list()
        fetched_documents = []
        fetched_documents = groups_object.get_groups_details_documents(
            groups_schema=groups_schema,
            groups_data=groups_object.groups_list,
            enable_permission=self.enable_permission,
        )
        groups_data = fetched_documents["data"]
        self.queue.append_to_queue(groups_data)
        return groups_data

    def get_recordings(self, partitioned_users_list):
        """This method fetches the recordings from Zoom server.
        :param partitioned_users_list: list of users for which recordings will be fetched.
        :returns: list of recordings documents.
        """
        fetched_documents = []
        recordings_schema = self.get_schema_fields(RECORDINGS)
        recordings_object = ZoomRecordings(
            self.config,
            self.logger,
            self.zoom_client,
            self.zoom_enterprise_search_mappings,
        )
        fetched_documents = recordings_object.get_recordings_details_documents(
            users_data=partitioned_users_list,
            recordings_schema=recordings_schema,
            start_time=self.objects_time_range[RECORDINGS][0],
            end_time=self.objects_time_range[RECORDINGS][1],
            enable_permission=self.enable_permission,
        )
        recording_data = fetched_documents["data"]
        return recording_data

    def get_channels(self, partitioned_users_list):
        """This method fetches the channels from Zoom server.
        :param partitioned_users_list: list of users for which channels will be fetched.
        :returns: list of channels documents.
        """
        fetched_documents = []
        channel_schema = self.get_schema_fields(CHANNELS)
        channels_object = ZoomChannels(
            self.config,
            self.logger,
            self.zoom_client,
            self.zoom_enterprise_search_mappings,
        )
        fetched_documents = channels_object.get_channels_details_documents(
            users_data=partitioned_users_list,
            channel_schema=channel_schema,
            enable_permission=self.enable_permission,
        )
        channels_data = fetched_documents["data"]
        return channels_data

    def perform_sync(self, parent_object, partitioned_users_list):
        """This method fetches all the objects from Zoom server and appends them to the
        shared queue and it returns list of locally stored details of documents fetched.
        :param parent_object: Parent object name.(ex.: ROLES or USERS(for indexing) and ROLES_FOR_DELETION or
            MULTITHREADED_OBJECTS_FOR_DELETION(for deletion))
        :param partitioned_users_list: list of dictionaries where each dictionary contains details fetched for
        a user from Zoom
        :returns: list of dictionary containing the properties (id, type, parent_id, created_at) of
            all the documents generated for the zoom objects (users, chats, meetings, roles,
            past-meetings, groups, files, channels and recordings).
        """
        if not partitioned_users_list or self.configuration_objects is None:
            return []
        try:
            documents_to_index = []
            ids_storage = []
            if parent_object == ROLES:
                roles_object = ZoomRoles(
                    self.config,
                    self.logger,
                    self.zoom_client,
                    self.zoom_enterprise_search_mappings,
                )
                self.all_chat_access = roles_object.fetch_user_ids_with_chat_access()
                if ROLES in self.configuration_objects:
                    self.logger.info(
                        f"Thread: [{threading.get_ident()}] fetching {ROLES}."
                    )
                    documents_to_index.extend(
                        self.fetch_roles_and_append_to_queue(roles_object)
                    )
                if GROUPS in self.configuration_objects:
                    self.logger.info(
                        f"Thread: [{threading.get_ident()}] fetching {GROUPS}."
                    )
                    groups_object = ZoomGroups(
                        self.config,
                        self.logger,
                        self.zoom_client,
                    )
                    documents_to_index.extend(
                        self.fetch_groups_and_append_to_queue(groups_object)
                    )

            elif parent_object == USERS or parent_object == MULTITHREADED_OBJECTS_FOR_DELETION:
                if USERS in self.configuration_objects and parent_object != MULTITHREADED_OBJECTS_FOR_DELETION:
                    self.logger.info(
                        f"Thread: [{threading.get_ident()}] fetching {USERS}."
                    )
                    documents_to_index.extend(
                        self.fetch_users_and_append_to_queue(partitioned_users_list)
                    )
                if (
                    parent_object != MULTITHREADED_OBJECTS_FOR_DELETION and (
                        MEETINGS in self.configuration_objects or PAST_MEETINGS in self.configuration_objects
                    )
                ):
                    is_meetings_in_objects = False
                    if MEETINGS in self.configuration_objects:
                        is_meetings_in_objects = True
                        self.logger.info(
                            f"Thread: [{threading.get_ident()}] fetching {MEETINGS}."
                        )
                    meetings_object = ZoomMeetings(
                        self.config,
                        self.logger,
                        self.zoom_client,
                        self.zoom_enterprise_search_mappings,
                    )
                    meetings_documents = self.get_meetings(
                        partitioned_users_list,
                        meetings_object,
                        is_meetings_in_objects,
                    )
                    documents_to_index.extend(meetings_documents)
                    self.queue.append_to_queue(meetings_documents)
                if PAST_MEETINGS in self.configuration_objects and parent_object != MULTITHREADED_OBJECTS_FOR_DELETION:
                    self.logger.info(
                        f"Thread: [{threading.get_ident()}] fetching {PAST_MEETINGS}."
                    )
                    past_meetings_documents = self.get_past_meetings(meetings_object)
                    documents_to_index.extend(past_meetings_documents)
                    self.queue.append_to_queue(past_meetings_documents)
                if RECORDINGS in self.configuration_objects:
                    recordings_documents = self.get_recordings(
                        partitioned_users_list,
                    )
                    documents_to_index.extend(recordings_documents)
                    if parent_object != MULTITHREADED_OBJECTS_FOR_DELETION:
                        self.queue.append_to_queue(recordings_documents)
                if CHANNELS in self.configuration_objects:
                    channels_documents = self.get_channels(
                        partitioned_users_list,
                    )
                    documents_to_index.extend(channels_documents)
                    if parent_object != MULTITHREADED_OBJECTS_FOR_DELETION:
                        self.queue.append_to_queue(channels_documents)

                if CHATS in self.configuration_objects:
                    user_ids_list = []
                    for user in partitioned_users_list:
                        user_ids_list.append(user["id"])
                    chat_access_enabled_users = [
                        user_id
                        for user_id in self.all_chat_access
                        if user_id in user_ids_list
                    ]
                    chats_files_object = ZoomChatMessages(
                        self.config,
                        self.logger,
                        self.zoom_client,
                        self.zoom_enterprise_search_mappings,
                    )
                    fetched_documents = []
                    chats_schema = self.get_schema_fields(CHATS)
                    fetched_documents = chats_files_object.get_chat_messages(
                        users_data=chat_access_enabled_users,
                        chats_schema=chats_schema,
                        start_time=self.objects_time_range[CHATS][0],
                        end_time=self.objects_time_range[CHATS][1],
                        enable_permission=self.enable_permission,
                    )
                    chats_documents = fetched_documents["data"]
                    documents_to_index.extend(chats_documents)
                    if parent_object != MULTITHREADED_OBJECTS_FOR_DELETION:
                        self.queue.append_to_queue(chats_documents)
        except Exception as exception:
            self.logger.error(
                f"{[threading.get_ident()]} Error while fetching objects. Error: {exception}"
            )
        for document in documents_to_index:
            ids_storage.append(
                {
                    "id": str(document["id"]),
                    "type": document["type"],
                    "parent_id": document.get("parent_id", ""),
                    "created_at": document.get("created_at", ""),
                }
            )
        return ids_storage
