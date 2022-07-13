#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a full sync against the source.

    It will attempt to sync absolutely all documents that are available in the
    third-party system and ingest them into Enterprise Search instance.
"""

from datetime import datetime

from .base_command import BaseCommand
from .checkpointing import Checkpoint
from .connector_queue import ConnectorQueue
from .constant import GROUPS, RFC_3339_DATETIME_FORMAT, ROLES, USERS
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_zoom import SyncZoom
from .utils import get_current_time

INDEXING_TYPE = "full"


class FullSyncCommand(BaseCommand):
    """This class start execution of fullsync feature."""

    def start_producer(self, queue):
        """This method starts async calls for the producer which is responsible for fetching documents from
        the Zoom and push those documents in the shared queue.
        :param queue: Shared queue to fetch the stored documents
        """
        self.logger.debug("Starting the full sync..")
        current_time = get_current_time()
        objects_time_range = {}
        thread_count = self.config.get_value("zoom_sync_thread_count")
        for object_type in self.config.get_value("objects"):
            if object_type in [ROLES, GROUPS]:
                continue
            start_time_end_time_list = [
                (
                    datetime.strptime(
                        self.config.get_value("start_time"),
                        RFC_3339_DATETIME_FORMAT,
                    )
                ),
                (
                    datetime.strptime(
                        current_time,
                        RFC_3339_DATETIME_FORMAT,
                    )
                ),
            ]
            objects_time_range[object_type] = start_time_end_time_list
        try:
            sync_zoom = SyncZoom(
                self.config,
                self.logger,
                self.workplace_search_client,
                self.zoom_client,
                objects_time_range,
                queue,
                self.zoom_enterprise_search_mappings,
            )
            partitioned_users_lists = sync_zoom.get_all_users_from_zoom()
            fetched_roles_id_list = sync_zoom.perform_sync(ROLES, [{}])
            metadata_of_fetched_documents = self.create_and_execute_jobs(
                thread_count,
                sync_zoom.perform_sync,
                (USERS,),
                partitioned_users_lists,
            )
            metadata_of_fetched_documents.extend(fetched_roles_id_list)
            for object_type in self.config.get_value("objects"):
                if object_type in [ROLES, GROUPS]:
                    continue
                queue.put_checkpoint(object_type, current_time, INDEXING_TYPE)

            # Send end signals for each live threads to notify them to close watching the queue
            # for any incoming documents
            for _ in range(
                self.config.get_value("enterprise_search_sync_thread_count")
            ):
                queue.end_signal()
        except Exception as exception:
            self.logger.error(
                "Error while Fetching from the Zoom. Checkpoint not saved"
            )
            raise exception

        return metadata_of_fetched_documents

    def start_consumer(self, queue, metadata_of_fetched_documents):
        """This method starts async calls for the consumer which is responsible for indexing documents to the
        Enterprise Search.After successful indexing it stores checkpoints of time dependent objects and updates
        the doc_id according to indexed documents.
        :param queue: Shared queue to fetch the stored documents
        :param metadata_of_fetched_documents: updated list of dictionary for local storage documents.
        """
        checkpoint = Checkpoint(self.config, self.logger)
        thread_count = self.config.get_value("enterprise_search_sync_thread_count")
        sync_es = SyncEnterpriseSearch(
            self.config, self.logger, self.workplace_search_client, queue
        )

        generated_documents_ids, indexed_documents_ids = self.create_and_execute_jobs(
            thread_count, sync_es.perform_sync, (), None
        )
        if not sync_es.is_error_ocurred:
            for checkpoint_item in sync_es.checkpoints:
                checkpoint.set_checkpoint(
                    checkpoint_item[0], checkpoint_item[1], checkpoint_item[2]
                )
        self.logger.info(
            f"SUMMARY : Total {len(indexed_documents_ids)} documents indexed out of {len(generated_documents_ids)}"
        )
        self.local_storage.store_indexed_documents_ids(
            metadata_of_fetched_documents, indexed_documents_ids
        )

    def execute(self):
        """This function execute the full sync."""
        current_time = get_current_time()
        self.logger.info(f"Indexing started at: {current_time}")
        queue = ConnectorQueue(self.logger)
        metadata_of_fetched_documents = self.start_producer(queue)
        self.start_consumer(queue, metadata_of_fetched_documents)
        self.logger.info(f"Indexing ended at: {get_current_time()}")
