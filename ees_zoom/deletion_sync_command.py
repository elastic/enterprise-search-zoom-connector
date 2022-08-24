#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
""" This module allows to remove recently deleted documents from Elastic Enterprise Search.
    Documents that were deleted in Zoom will still be available in Elastic Enterprise Search
    until this module is used.
"""

from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta
from iteration_utilities import unique_everseen

from .base_command import BaseCommand
from .constant import (BATCH_SIZE, CHANNELS, CHATS, FILES, GROUPS, MEETINGS,
                       PAST_MEETINGS, RECORDINGS, RFC_3339_DATETIME_FORMAT,
                       ROLES, USERS)
from .sync_zoom import SyncZoom
from .utils import (get_current_time,
                    split_documents_into_equal_chunks)

MULTITHREADED_OBJECTS_FOR_DELETION = "multithreaded_objects_for_deletion"
ROLES_FOR_DELETION = "roles_for_deletion"
SIX_MONTHS = "six_months"
ONE_MONTH = "one_month"
# few zoom objects have a time limitation on their APIs. (For example meetings older than 1 month can't be fetched from the Zoom APIs)
TIME_RANGE_LIMIT_OBJECTS = [MEETINGS, PAST_MEETINGS, CHATS, FILES, RECORDINGS]


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
                raise

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
                raise

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
                    raise
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for"
                    f"{PAST_MEETINGS} from zoom. Error: {exception}"
                )
                raise

        for document in delete_keys_list:
            if document["type"] == PAST_MEETINGS and document["parent_id"] in past_meetings_deletion_ids_list:
                self.global_deletion_ids.append(str(document["id"]))

    def collect_channels_and_recordings_ids(
        self,
        channels_and_recordings_ids,
    ):
        """This function is used to collect document ids to be deleted from
        enterprise-search for channels, recordings, chats and files object.
        :param channels_and_recordings_ids: list of channels, recording, chat
        and file documents ids.
        which are present in enterprise-search.
        """
        self.logger.info(
            "Started collecting object_ids to be deleted from enterprise search for:"
            f" {CHANNELS}, {RECORDINGS}, {CHATS} and {FILES}"
        )
        try:
            objects_time_range = {}
            for time_dependent_object in self.config.get_value("objects"):
                if time_dependent_object in [RECORDINGS, CHATS, FILES]:
                    objects_time_range[time_dependent_object] = [
                        (
                            datetime.strptime(
                                self.start_time,
                                RFC_3339_DATETIME_FORMAT,
                            )
                        ),
                        (
                            datetime.strptime(
                                self.end_time,
                                RFC_3339_DATETIME_FORMAT,
                            )
                        ),
                    ]

            sync_zoom = SyncZoom(
                self.config,
                self.logger,
                self.workplace_search_client,
                self.zoom_client,
                objects_time_range,
                {},
                {},
            )
            partitioned_users_buckets = sync_zoom.get_all_users_from_zoom()
            _ = sync_zoom.perform_sync(ROLES_FOR_DELETION, [{}])
            global_keys = self.create_and_execute_jobs(
                self.zoom_sync_thread_count,
                sync_zoom.perform_sync,
                (MULTITHREADED_OBJECTS_FOR_DELETION,),
                partitioned_users_buckets,
            )
        except Exception:
            self.logger.error(
                f"Error while checking objects: {CHANNELS}, {RECORDINGS}, {CHATS} and {FILES} for deletion from zoom."
            )
            raise

        fetched_objects_ids = [str(document["id"]) for document in global_keys]

        for doc_id in channels_and_recordings_ids:
            if str(doc_id) not in fetched_objects_ids:
                self.global_deletion_ids.append(str(doc_id))

    def omitted_document(
        self, document, deleted_ids_list, chats_and_files_id, time_limit
    ):
        """This method will return object document list if object document is archived by the Zoom APIs.
        :param document: dictionary of object document present in delete_keys of doc_id storage.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :param chats_and_files_id: chats and files documents ids present in delete_keys of doc_id.json file.
        :param time_limit: string of time-limit type.(ex: six_months_ago or one_month_ago)
        :returns: it will return list of document dictionary if document is archived.
        """
        # This block will detect if the parent user of an object is deleted from Zoom or not.
        if document["parent_id"] not in deleted_ids_list:
            return [document]
        # This block will detect if more than 1 document of SIX_MONTHS limit object exist in storage or not.
        if time_limit == SIX_MONTHS and chats_and_files_id.count(document["id"]) > 1:
            return [document]
        return []

    def refresh_storage(self, deleted_ids_list, chats_and_files_id):
        """This method is used to refresh the ids stored in doc_id.json file.
        It will omit the documents from the delete_keys of doc_id.json file
        for the time restricted objects if they can't be fetched from the Zoom API endpoints and
        it will return updated storage collection of of doc_id.json file.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :param chats_and_files_id: list of chats and files documents ids present in delete_keys of doc_id.json file.
        :returns: storage collection of of doc_id.json file.
        """
        storage_with_collection = self.local_storage.load_storage()
        # chats and files objects older than last six months can't be fetched from the Zoom APIs
        six_months_ago = datetime.strptime(
            get_current_time(),
            RFC_3339_DATETIME_FORMAT,
        ) + relativedelta(days=-180)
        # recordings, meetings and past_meetings objects older than last month can't be fetched from the Zoom API
        one_month_ago = datetime.strptime(
            get_current_time(),
            RFC_3339_DATETIME_FORMAT,
        ) + relativedelta(days=-30)
        documents_list_to_omit = []
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in [CHATS, FILES] and datetime.strptime(document["created_at"], RFC_3339_DATETIME_FORMAT) < six_months_ago:
                documents_list_to_omit.extend(
                    self.omitted_document(
                        document,
                        deleted_ids_list,
                        chats_and_files_id,
                        SIX_MONTHS,
                    )
                )
            elif document["type"] in [RECORDINGS, PAST_MEETINGS, MEETINGS] and datetime.strptime(document["created_at"], RFC_3339_DATETIME_FORMAT) < one_month_ago:
                documents_list_to_omit.extend(
                    self.omitted_document(
                        document,
                        deleted_ids_list,
                        [],
                        ONE_MONTH,
                    )
                )

        for document in documents_list_to_omit:
            storage_with_collection["delete_keys"].remove(document)
            storage_with_collection["global_keys"].remove(document)

        self.local_storage.update_storage(storage_with_collection)

        return storage_with_collection

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
            CHANNELS: [],
            RECORDINGS: [],
            CHATS: [],
            FILES: [],
        }
        for document in ids_collection["delete_keys"]:
            if document["type"] in [ROLES, GROUPS, USERS, CHANNELS, CHATS, FILES]:
                delete_key_ids[document["type"]].append(document["id"])
        if ROLES in self.configuration_objects and delete_key_ids[ROLES]:
            self.collect_deleted_roles_ids(delete_key_ids[ROLES])
        for object_type in [GROUPS, USERS]:
            if (
                object_type in self.configuration_objects and delete_key_ids[object_type]
            ):
                self.collect_deleted_ids(delete_key_ids[object_type], object_type)

        chats_and_files_id = delete_key_ids[CHATS] + delete_key_ids[FILES]
        storage_with_collection = self.refresh_storage(
            self.global_deletion_ids, chats_and_files_id
        )

        (
            delete_key_ids[CHATS],
            delete_key_ids[FILES],
        ) = ([], [])

        # collecting the time range limit objects ids after refreshing the local storage.
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in TIME_RANGE_LIMIT_OBJECTS:
                delete_key_ids[document["type"]].append(
                    document["parent_id"]
                    if document["type"] == PAST_MEETINGS
                    else document["id"]
                )

        for object_type in [MEETINGS, PAST_MEETINGS]:
            if object_type in self.configuration_objects and delete_key_ids[object_type]:
                if object_type == MEETINGS:
                    self.collect_deleted_ids(
                        delete_key_ids[MEETINGS], MEETINGS
                    )
                else:
                    self.collect_past_deleted_meetings(
                        delete_key_ids[PAST_MEETINGS],
                        storage_with_collection["delete_keys"],
                    )

        channels_and_recordings_ids = []
        for object_type in [CHANNELS, CHATS, FILES, RECORDINGS]:
            if object_type in self.configuration_objects and delete_key_ids[object_type]:
                channels_and_recordings_ids.extend(delete_key_ids[object_type])

        if channels_and_recordings_ids:
            self.collect_channels_and_recordings_ids(channels_and_recordings_ids)

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
