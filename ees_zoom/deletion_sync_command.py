#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
""" This module allows to remove recently deleted documents from Elastic Enterprise Search.
    Documents that were deleted in Zoom will still be available in Elastic Enterprise Search
    until this module is used.
"""
from datetime import time

import requests
from iteration_utilities import unique_everseen

from .base_command import BaseCommand
from .constant import (BATCH_SIZE, GROUPS,
                       ROLES, USERS)
from .utils import (get_current_time, retry,
                    split_documents_into_equal_chunks)

MULTITHREADED_OBJECTS_FOR_DELETION = "multithreaded_objects_for_deletion"
ROLES_FOR_DELETION = "roles_for_deletion"


class DeletionSyncCommand(BaseCommand):
    """DeletionSyncCommand class allows to remove instances of specific objects.
    It provides a way to remove those objects from Elastic Enterprise Search
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

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def collect_deleted_ids(self, object_ids_list, object_type):
        """This function is used to collect document ids to be deleted from
        enterprise-search for users, and groups object.
        :param object_ids_list: object_ids list currently present in enterprise-search.
        :param object_type: different object type like users, meetings and groups object.
        """
        self.logger.info(
            f"Started collecting object_ids to be deleted from enterprise search for: {object_type}"
        )
        object_id_index = 0
        while object_id_index < len(object_ids_list):
            try:
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                url = f"https://api.zoom.us/v2/{object_type}/{object_ids_list[object_id_index]}"
                object_response = requests.get(url=url, headers=headers)
                if (
                    object_response.text and object_response.status_code == 404 or object_response.status_code == 400
                ):
                    self.global_deletion_ids.append(object_ids_list[object_id_index])
                elif object_response.status_code == 401:
                    if time.time() > self.zoom_client.access_token_expiration:
                        self.zoom_client.get_token()
                    continue
                else:
                    object_response.raise_for_status()
                object_id_index += 1
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exception:
                self.logger.exception(
                    f"Exception raised while performing deletion sync for {object_type} from Zoom: {exception}"
                )
                raise exception
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for {object_type} from zoom : {exception}"
                )
                raise exception

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def collect_deleted_roles_ids(self, roles_ids_list):
        """This function is used to collect document ids to be deleted from
        enterprise-search for roles object.
         :param roles_ids_list: list of documents ids for roles object which are present in enterprise-search.
        """
        self.logger.info(
            f"Started collecting object_ids to be deleted from enterprise search for: {ROLES}"
        )
        role_id_index = 0
        while role_id_index < len(roles_ids_list):
            try:
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                url = f"https://api.zoom.us/v2/roles/{roles_ids_list[role_id_index]}"
                role_response = requests.get(url=url, headers=headers)
                if role_response.text and role_response.status_code == 300:
                    self.global_deletion_ids.append(roles_ids_list[role_id_index])
                elif role_response.status_code == 401:
                    if time.time() > self.zoom_client.access_token_expiration:
                        self.zoom_client.get_token()
                    continue
                else:
                    role_response.raise_for_status()
                role_id_index += 1
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exception:
                self.logger.exception(
                    f"Exception raised while performing deletion sync for {ROLES} from Zoom: {exception}"
                )
                raise exception
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for {ROLES} from zoom : {exception}"
                )
                raise exception

    def omitted_document(
        self, document, deleted_ids_list, time_limit
    ):
        """This method will return object document list if object document is archived by the Zoom APIs.
        :param document: dictionary of object document present in delete_keys of doc_id storage.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :param time_limit: string of time-limit type.(ex: six_months_time or one_month_time)
        :returns: it will return list of document dictionary if document is archived.
        """
        # This block will detect if the parent user of an object is deleted from Zoom or not.
        if document["parent_id"] not in deleted_ids_list:
            return [document]
        return []

    def execute(self):
        """This function will start the execution of DeletionSync Module."""
        logger = self.logger
        logger.debug("Starting the execution of deletion sync....")
        ids_collection = self.local_storage.load_storage()
        delete_key_ids = {
            USERS: [],
            ROLES: [],
            GROUPS: [],
        }
        for document in ids_collection["delete_keys"]:
            if document["type"] in [ROLES, GROUPS, USERS]:
                delete_key_ids[document["type"]].append(document["id"])
        self.zoom_client.get_token()
        if ROLES in self.configuration_objects and delete_key_ids[ROLES]:
            self.collect_deleted_roles_ids(delete_key_ids[ROLES])
        for object_type in [GROUPS, USERS]:
            if (
                object_type in self.configuration_objects and delete_key_ids[object_type]
            ):
                self.collect_deleted_ids(delete_key_ids[object_type], object_type)

        storage_with_collection = self.local_storage.load_storage()
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
