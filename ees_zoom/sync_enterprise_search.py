#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.
    It's possible to run full syncs and incremental syncs with this module.
"""
import threading

from iteration_utilities import unique_everseen


from .constant import BATCH_SIZE
from .utils import (split_by_max_cumulative_length,
                    split_documents_into_equal_chunks)


class SyncEnterpriseSearch:
    """This class contains common logic for indexing to workplace search"""

    def __init__(self, config, logger, workplace_search_client, queue):
        self.config = config
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.queue = queue
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.enterprise_search_sync_thread_count = config.get_value(
            "enterprise_search_sync_thread_count"
        )
        self.indexed_documents_ids = set()
        self.generated_documents_ids = set()
        self.total_document_indexed = 0
        self.total_documents_found = 0
        self.checkpoints = []
        self.is_error_ocurred = False
        self.max_allowed_bytes = 10000000

    def index_documents(self, documents):
        """This method indexes the documents to the Enterprise Search.
        :param documents: list of documents to be indexed
        """
        self.total_documents_found += len(documents)
        try:
            if documents:
                documents_indexed = 0
                responses = self.workplace_search_client.index_documents(
                    content_source_id=self.ws_source,
                    documents=documents,
                )
                for document in responses["results"]:
                    if not document["errors"]:
                        documents_indexed += 1
                        self.indexed_documents_ids.add(document["id"])
                    else:
                        self.logger.error(
                            f"Unable to index the document with id: {document['id']} Error {document['errors']}"
                        )
                self.total_document_indexed += documents_indexed
        except Exception as exception:
            self.logger.exception(f"Error while indexing the files. Error: {exception}")
            raise exception

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        try:
            signal_open = True
            while signal_open:
                documents_to_index = []
                while len(documents_to_index) < BATCH_SIZE and len(str(documents_to_index)) < self.max_allowed_bytes:
                    documents = self.queue.get()
                    if documents.get("type") == "signal_close":
                        self.logger.info(
                            f"Found an end signal in the queue. Closing Thread ID {threading.get_ident()}"
                        )
                        signal_open = False
                        break
                    elif documents.get("type") == "checkpoint":
                        self.checkpoints.append(
                            [
                                documents.get("data")[0],
                                documents.get("data")[1],
                                documents.get("data")[2],
                            ]
                        )
                        break
                    else:
                        documents_to_index.extend(documents.get("data"))
                # This loop is to ensure if the last document fetched from the queue exceeds the size of
                # documents_to_index to more than the permitted chunk size, then we split the documents as per the limit
                documents_to_index = list(unique_everseen(documents_to_index))
                for document_list in split_documents_into_equal_chunks(
                    documents_to_index, BATCH_SIZE
                ):
                    for documents in split_by_max_cumulative_length(
                        document_list, self.max_allowed_bytes
                    ):
                        self.index_documents(documents)
                    for document in document_list:
                        self.generated_documents_ids.add(document["id"])
        except Exception as exception:
            self.logger.error(exception)
            self.is_error_ocurred = True
            raise exception
        self.logger.info(
            f"Thread: [{threading.get_ident()}] Total {self.total_document_indexed} documents "
            f"indexed out of: {self.total_documents_found} till now.."
        )
        return self.generated_documents_ids, self.indexed_documents_ids
