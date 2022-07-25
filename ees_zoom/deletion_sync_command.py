#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in source will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""

import requests
from iteration_utilities import unique_everseen

from .base_command import BaseCommand
from .constant import (BATCH_SIZE, GROUPS, MEETINGS, PAST_MEETINGS,
                       ROLES, USERS)
from .utils import (get_current_time,
                    split_documents_into_equal_chunks)

# few zoom objects have a time limitation on their APIs. (For example meetings older than 1 month can't be fetched from the Zoom APIs)
TIME_RANGE_LIMIT_OBJECTS = [MEETINGS, PAST_MEETINGS]


class DeletionSyncCommand(BaseCommand):
    """DeletionSyncCommand class allows to remove instances of specific files.

    It provides a way to remove those files from Elastic Enterprise Search
    that were deleted in source Server instance."""

    def __init__(self, args):
        super().__init__(args)
        self.logger.debug("Initializing the deletion sync")
        config = self.config
        self.zoom_sync_thread_count = config.get_value("zoom_sync_thread_count")
        self.retry_count = config.get_value("retry_count")
        self.start_time = config.get_value("start_time")
        self.configuration_objects = config.get_value("objects")
        self.end_time = get_current_time()
        self.global_deletion_ids = []

    def delete_documents(self, ids_list, storage_with_collection):
        """Deletes the documents of specified ids from Workplace Search
        :param ids_list: list of ids to delete the documents from Workplace Search
        :param storage_with_collection: structure containing document dictionary of all objects.
        Returns:
            ids: updated structure containing document dictionary of all objects after performing deletion.
        """
        if ids_list:
            for chunk in split_documents_into_equal_chunks(ids_list, BATCH_SIZE):
                self.workplace_search_client.delete_documents(
                    document_ids=chunk,
                )
            document_id_index = 0
            size_of_collection = len(storage_with_collection["global_keys"])
            while document_id_index < size_of_collection:
                if storage_with_collection["global_keys"][document_id_index]["id"] in ids_list:
                    storage_with_collection["global_keys"].pop(document_id_index)
                    size_of_collection -= 1
                    continue
                document_id_index += 1
        return storage_with_collection

    def collect_deleted_ids(self, object_ids_list, object_type):
        """This function is used to collect document ids to be deleted from
        enterprise-search for users, groups, and meetings object.
        :param object_ids_list: object_ids list currently present in enterprise-search.
        :param object_type: different object type like users, meetings and groups object.
        """
        self.logger.info(
            f"Started collecting object_ids to be deleted from enterprise search for: {object_type}"
        )
        for object_id in object_ids_list:
            try:
                _ = self.zoom_client.get(
                    end_point=f"{object_type}/{object_id}", key=object_type
                )
            except requests.exceptions.HTTPError as HTTPException:
                if HTTPException.__dict__["response"].status_code in [
                    404,
                    400,
                ]:
                    # Append the deleted documents to the global_deletion_ids list which will be iterated to ensure those documents are deleted from the Enterprise Search as well
                    self.global_deletion_ids.append(object_id)
                else:
                    raise
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for"
                    f"{object_type} from zoom. Error: {exception}"
                )
                raise exception

    def collect_deleted_roles_ids(self, roles_ids_list):
        """This function is used to collect document ids to be deleted from
        enterprise-search for roles object.
         :param roles_ids_list: list of documents ids for roles object which are present in enterprise-search.
        """
        self.logger.info(
            f"Started collecting object_ids to be deleted from enterprise search for: {ROLES}"
        )
        for role_id in roles_ids_list:
            try:
                _ = self.zoom_client.get(end_point=f"roles/{role_id}", key="privileges")
            except requests.exceptions.HTTPError as HTTPException:
                # Getting error code 400 but the zoom api documentation is suggesting error code 300
                if HTTPException.__dict__["response"].status_code in [300, 400]:
                    # Append the deleted documents to the global_deletion_ids list which will be iterated to ensure those documents are deleted from the Enterprise Search as well
                    self.global_deletion_ids.append(role_id)
                else:
                    raise
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for {ROLES} from zoom. Error: {exception}"
                )
                raise exception

    def collect_past_deleted_meetings(self, past_meetings_ids_list, delete_keys_list):
        """This function is used to collect document ids to be deleted from
        enterprise-search for past_meetings object.
        :param past_meetings_ids_list: list of documents ids for past_meetings object
                                       which are present in enterprise-search.
        :param delete_keys_list: list of dictionary for delete_keys in local storage.
        """
        self.logger.info(
            f"Started collecting object_ids to be deleted from enterprise search for: {PAST_MEETINGS}"
        )
        past_meetings_deletion_ids_list = []
        for past_meeting_id in past_meetings_ids_list:
            try:
                _ = self.zoom_client.get(end_point=f"past_meetings/{past_meeting_id}", key=PAST_MEETINGS)
            except requests.exceptions.HTTPError as HTTPException:
                if HTTPException.__dict__[
                    "response"
                ].status_code in [
                    404,
                    400,
                ]:
                    # Append the deleted documents to the global_deletion_ids list which will be iterated to ensure those documents are deleted from the Enterprise Search as well
                    past_meetings_deletion_ids_list.append(past_meeting_id)
                else:
                    raise HTTPException
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for"
                    f"{PAST_MEETINGS} from zoom. Error: {exception}"
                )
                raise exception

        for document in delete_keys_list:
            if document["type"] == PAST_MEETINGS and document["parent_id"] in past_meetings_deletion_ids_list:
                self.global_deletion_ids.append(str(document["id"]))

    def execute(self):
        """Runs the deletion sync logic"""
        logger = self.logger
        logger.debug("Starting the execution of deletion sync....")
        ids_collection = self.local_storage.load_storage()
        delete_key_ids = {
            USERS: [],
            ROLES: [],
            GROUPS: [],
            MEETINGS: [],
            PAST_MEETINGS: [],
        }
        for document in ids_collection["delete_keys"]:
            if document["type"] in [ROLES, GROUPS, USERS]:
                delete_key_ids[document["type"]].append(document["id"])
        if ROLES in self.configuration_objects and delete_key_ids[ROLES]:
            self.collect_deleted_roles_ids(delete_key_ids[ROLES])
        for object_type in [GROUPS, USERS]:
            if (
                object_type in self.configuration_objects and delete_key_ids[object_type]
            ):
                self.collect_deleted_ids(delete_key_ids[object_type], object_type)

        storage_with_collection = self.local_storage.load_storage()

        for document in storage_with_collection["delete_keys"]:
            if document["type"] in TIME_RANGE_LIMIT_OBJECTS:
                delete_key_ids[document["type"]].append(
                    document["parent_id"]
                    if document["type"] == PAST_MEETINGS
                    else document["id"]
                )

        for object_type in [MEETINGS, PAST_MEETINGS]:
            if object_type in self.configuration_objects and delete_key_ids[object_type]:
                self.collect_deleted_ids(
                    delete_key_ids[MEETINGS], MEETINGS
                ) if object_type == MEETINGS else self.collect_past_deleted_meetings(
                    delete_key_ids[PAST_MEETINGS],
                    storage_with_collection["delete_keys"],
                )

        if self.global_deletion_ids:
            storage_with_collection = self.delete_documents(
                list(unique_everseen(self.global_deletion_ids)),
                storage_with_collection,
            )
            self.logger.info("Completed the deletion of documents.")
        else:
            self.logger.info("No documents are present to be deleted from the enterprise search.")
        storage_with_collection["delete_keys"] = []
        self.logger.info("Updating the local storage")
        self.local_storage.update_storage(storage_with_collection)
