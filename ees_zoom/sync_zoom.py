#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""sync_zoom module allows to sync data to Elastic Enterprise Search.
It's possible to run full syncs and incremental syncs with this module."""
import threading

from .adapter import DEFAULT_SCHEMA
from .constant import GROUPS, ROLES, USERS
from .utils import split_list_into_buckets
from .zoom_groups import ZoomGroups
from .zoom_roles import ZoomRoles


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
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.configuration_objects = config.get_value("objects")
        self.enable_permission = config.get_value("enable_document_permission")
        self.zoom_sync_thread_count = config.get_value("zoom_sync_thread_count")
        self.mapping_sheet_path = config.get_value("zoom.user_mapping")

    def get_schema_fields(self, document_name):
        """Returns the schema of all the include_fields or exclude_fields specified in the configuration file.
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
            roles_object.roles_list, self.config.get_value("zoom_sync_thread_count")
        )
        for roles in roles_list:
            fetched_documents = roles_object.get_roles_details_documents(
                roles_schema,
                roles,
                self.enable_permission,
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
            groups_schema,
            groups_object.groups_list,
            self.enable_permission,
        )
        groups_data = fetched_documents["data"]
        self.queue.append_to_queue(groups_data)
        return groups_data

    def perform_sync(self, parent_object, partitioned_users_bucket):
        """This method fetches all the objects from Zoom server and appends them to the
        shared queue and it returns list of locally stored details of documents fetched.
        :param parent_object: Parent object name (ex. roles or users)
        :param partitioned_users_bucket: list of partitioned_users_bucket dictionary
        :returns: list of dictionary containing the id, type, parent_id,
                    created_at property of all the users, chats, meetings, roles,
                    past-meetings and recordings the generated document.
        """
        if not partitioned_users_bucket or self.configuration_objects is None:
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

            elif parent_object == USERS:
                # indexing of objects based on user id.
                pass
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
