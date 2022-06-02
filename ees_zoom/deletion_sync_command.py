#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in source will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""
from datetime import datetime, time

import requests
from dateutil.relativedelta import relativedelta
from iteration_utilities import unique_everseen

from .base_command import BaseCommand
from .constant import (BATCH_SIZE, GROUPS, MEETINGS,
                       PAST_MEETINGS, RFC_3339_DATETIME_FORMAT,
                       ROLES, USERS)
from .utils import (get_current_time, is_within_time_range, retry,
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

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def collect_deleted_ids(self, object_ids_list, object_type):
        """This function is used to collect document ids to be deleted from
        enterprise-search for users, meetings, and groups object.
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

    @retry(
        exception_list=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )
    )
    def collect_deleted_past_meetings(self, past_meetings_ids_list, delete_keys_list):
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
        meeting_id_index = 0
        while meeting_id_index < len(past_meetings_ids_list):
            try:
                headers = {
                    "authorization": f"Bearer {self.zoom_client.access_token}",
                    "content-type": "application/json",
                }
                url = f"https://api.zoom.us/v2/past_meetings/{past_meetings_ids_list[meeting_id_index]}"
                past_meeting_response = requests.get(url=url, headers=headers)
                if (
                    past_meeting_response.text and past_meeting_response.status_code == 404 or past_meeting_response.status_code == 400
                ):
                    past_meetings_deletion_ids_list.append(
                        past_meetings_ids_list[meeting_id_index]
                    )
                elif past_meeting_response.status_code == 401:
                    if time.time() > self.zoom_client.access_token_expiration:
                        self.zoom_client.get_token()
                    continue
                else:
                    past_meeting_response.raise_for_status()
                meeting_id_index += 1
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exception:
                self.logger.exception(
                    f"Exception raised while performing deletion sync for {PAST_MEETINGS} from Zoom: {exception}"
                )
                raise exception
            except Exception as exception:
                self.logger.exception(
                    f"Unknown error occurred while performing deletion sync for {PAST_MEETINGS} from zoom : {exception}"
                )
                raise exception

        for document in delete_keys_list:
            if (
                document["type"] == PAST_MEETINGS and document["parent_id"] in past_meetings_deletion_ids_list
            ):
                self.global_deletion_ids.append(str(document["id"]))

    def omitted_document(
        self, document, deleted_ids_list
    ):
        """This method will return object document list if object document is archived by the Zoom APIs.
        :param document: dictionary of object document present in delete_keys of doc_id storage.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :returns: it will return list of document dictionary if document is archived.
        """
        # This block will detect if the parent user of an object is deleted from Zoom or not.
        if document["parent_id"] not in deleted_ids_list:
            return [document]
        return []

    def refresh_storage(self, deleted_ids_list):
        """This method is used to refresh the ids stored in doc_id.json file.
        It will omit the documents from the delete_keys of doc_id.json file
        for the time restricted objects if they can't be fetched from the Zoom API endpoints and
        it will return updated storage collection of of doc_id.json file.
        :param deleted_ids_list: list of ids for deleted objects ids.
        :returns: storage collection of of doc_id.json file.
        """
        storage_with_collection = self.local_storage.load_storage()
        # meetings and past_meetings objects older than last month can't be fetched from the Zoom API
        one_month_time = datetime.strptime(
            get_current_time(),
            RFC_3339_DATETIME_FORMAT,
        ) + relativedelta(months=-1, days=+2)
        documents_list_to_omit = []
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in [
                PAST_MEETINGS,
                MEETINGS,
            ] and is_within_time_range(document, one_month_time):
                documents_list_to_omit.extend(
                    self.omitted_document(
                        document,
                        deleted_ids_list,
                    )
                )

        for document in documents_list_to_omit:
            storage_with_collection["delete_keys"].remove(document)
            storage_with_collection["global_keys"].remove(document)

        self.local_storage.update_storage(storage_with_collection)

        return storage_with_collection

    def execute(self):
        """This function will start the execution of DeletionSync Module."""
        logger = self.logger
        logger.debug("Starting the execution of deletion sync....")
        ids_collection = self.local_storage.load_storage()
        delete_key_ids = {
            USERS: [],
            MEETINGS: [],
            ROLES: [],
            PAST_MEETINGS: [],
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

        storage_with_collection = self.refresh_storage(self.global_deletion_ids)

        time_range_limit_objects = [MEETINGS, PAST_MEETINGS]
        # collecting the time range limit objects ids after refreshing the local storage.
        for document in storage_with_collection["delete_keys"]:
            if document["type"] in time_range_limit_objects:
                delete_key_ids[document["type"]].append(
                    document["parent_id"]
                    if document["type"] == PAST_MEETINGS
                    else document["id"]
                )

        for object_type in [MEETINGS, PAST_MEETINGS]:
            if (
                object_type in self.configuration_objects and delete_key_ids[object_type]
            ):
                self.collect_deleted_ids(
                    delete_key_ids[MEETINGS], MEETINGS
                ) if object_type == MEETINGS else self.collect_deleted_past_meetings(
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
