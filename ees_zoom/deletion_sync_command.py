#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in source will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""
from datetime import datetime

from dateutil.relativedelta import relativedelta
from iteration_utilities import unique_everseen

from .base_command import BaseCommand
from .constant import (BATCH_SIZE, CHATS, FILES,
                       RFC_3339_DATETIME_FORMAT)
from .sync_zoom import SyncZoom
from .utils import (get_current_time, is_within_time_range,
                    split_documents_into_equal_chunks)

MULTITHREADED_OBJECTS_FOR_DELETION = "multithreaded_objects_for_deletion"
ROLES_FOR_DELETION = "roles_for_deletion"


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
        self.ws_source = config.get_value("enterprise_search.source_id")
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
                    content_source_id=self.ws_source,
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

    def collect_multithreaded_objects_ids(
        self,
        multithreaded_objects_ids,
    ):
        """This function is used to collect document ids to be deleted from
        enterprise-search for channels, recordings, chats and files object.
        :param multithreaded_objects_ids: list of channels, recording, chat
        and file documents ids.
        which are present in enterprise-search.
        """
        self.logger.info(
            "Started collecting object_ids to be deleted from enterprise search for:"
            f"{CHATS} and {FILES}"
        )
        try:
            objects_time_range = {}
            for time_dependent_object in self.config.get_value("objects"):
                if time_dependent_object in [CHATS, FILES]:
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
                self.zoom_client,
                self.workplace_search_client,
                objects_time_range,
                {},
                {},
            )
            partitioned_users_buckets = sync_zoom.get_all_users_from_zoom()
            _ = sync_zoom.perform_sync(ROLES_FOR_DELETION, [{}])
            global_keys = self.create_jobs(
                self.zoom_sync_thread_count,
                sync_zoom.perform_sync,
                (MULTITHREADED_OBJECTS_FOR_DELETION,),
                partitioned_users_buckets,
            )
        except Exception as exception:
            self.logger.error(
                f"Error while checking objects: {CHATS} and {FILES} for deletion from zoom."
            )
            raise exception

        fetched_objects_ids = [str(document["id"]) for document in global_keys]

        for doc_id in multithreaded_objects_ids:
            if str(doc_id) not in fetched_objects_ids:
                self.global_deletion_ids.append(str(doc_id))

    def omitted_document(
        self, document, deleted_ids_list, chats_and_files_id, time_limit
    ):
        """This method will return object document list if object document is archived by the Zoom APIs.
        :param document: dictionary of object document present in delete_keys of doc_id storage.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :param chats_and_files_id: chats and files documents ids present in delete_keys of doc_id.json file.
        :param time_limit: string of time-limit type.(ex: six_months_time or one_month_time)
        :returns: it will return list of document dictionary if document is archived.
        """
        # This block will detect if the parent user of an object is deleted from Zoom or not.
        if document["parent_id"] not in deleted_ids_list:
            return [document]
        # This block will detect if more than 1 document of SIX_MONTHS limit object exist in storage or not.
        if time_limit == "SIX_MONTHS" and chats_and_files_id.count(document["id"]) > 1:
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
        six_months_time = datetime.strptime(
            get_current_time(),
            RFC_3339_DATETIME_FORMAT,
        ) + relativedelta(months=-6, days=+4)
        documents_list_to_omit = []
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in [CHATS, FILES] and is_within_time_range(
                document, six_months_time
            ):
                documents_list_to_omit.extend(
                    self.omitted_document(
                        document,
                        deleted_ids_list,
                        chats_and_files_id,
                        "SIX_MONTHS",
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
            CHATS: [],
            FILES: [],
        }
        for document in ids_collection["delete_keys"]:
            if document["type"] in [CHATS, FILES]:
                delete_key_ids[document["type"]].append(document["id"])
        self.zoom_client.get_token()
        chats_and_files_id = delete_key_ids[CHATS] + delete_key_ids[FILES]
        storage_with_collection = self.refresh_storage(
            self.global_deletion_ids, chats_and_files_id
        )

        (
            delete_key_ids[CHATS],
            delete_key_ids[FILES],
        ) = ([], [])

        time_range_limit_objects = [CHATS, FILES]
        # collecting the time range limit objects ids after refreshing the local storage.
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in time_range_limit_objects:
                delete_key_ids[document["type"]].append(document["id"])

        multithreaded_objects_ids = []
        for object_type in [CHATS, FILES]:
            if (
                object_type in self.configuration_objects and delete_key_ids[object_type]
            ):
                multithreaded_objects_ids.extend(delete_key_ids[object_type])

        if multithreaded_objects_ids:
            self.collect_multithreaded_objects_ids(
                multithreaded_objects_ids,
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
