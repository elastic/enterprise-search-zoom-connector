import logging
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.connector_queue import ConnectorQueue  # noqa
from ees_zoom.sync_enterprise_search import SyncEnterpriseSearch  # noqa
from elastic_enterprise_search import WorkplaceSearch  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads config from the file and returns it."""
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_indexing")
    return configuration, logger


def create_enterprise_search_obj():
    """This function create Enterprise Search object for test."""
    configs, logger = settings()
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    workplace_search_client = WorkplaceSearch(
        enterprise_search_host,
        http_auth=configs.get_value("enterprise_search.api_key"),
    )
    queue = ConnectorQueue()
    queue.end_signal()
    return SyncEnterpriseSearch(configs, logger, workplace_search_client, queue)


@pytest.mark.parametrize(
    "documents, mock_response, log_msg",
    [
        (
            [
                {
                    "id": 0,
                    "title": "file0",
                    "body": "Not much. It is a made up thing.",
                    "url": "dummy_folder/file0.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "text",
                },
                {
                    "id": 1,
                    "title": "file1",
                    "body": "Not much. It is a made up thing.",
                    "url": "dummy_folder/file1.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "text",
                },
            ],
            {"results": [{"id": "0", "errors": []}, {"id": "1", "errors": []}]},
            "Successfully indexed 2 to the workplace out of 2",
        )
    ],
)
def test_index_document(documents, mock_response, log_msg, caplog):
    """Test that index_document successfully index documents in Enterprise Search."""
    caplog.set_level("INFO")
    indexer_obj = create_enterprise_search_obj()
    indexer_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_response
    )
    indexer_obj.index_documents(documents)
    assert log_msg in caplog.text


@pytest.mark.parametrize(
    "documents, mock_response, log_level, error_msg",
    [
        (
            [
                {
                    "id": 0,
                    "title": "file0",
                    "body": "Not much. It is a made up thing.",
                    "url": "dummy_folder/file0.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "text",
                }
            ],
            {"results": [{"id": "0", "errors": ["not indexed"]}]},
            "ERROR",
            "Unable to index the document with id: 0",
        )
    ],
)
def test_index_document_when_error_occurs(
    documents, mock_response, log_level, error_msg, caplog
):
    """Test that index_document give proper error message if document not indexed."""
    caplog.set_level(log_level)
    indexer_obj = create_enterprise_search_obj()
    indexer_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_response
    )
    indexer_obj.index_documents(documents)
    assert error_msg in caplog.text


def test_perform_sync_enterprise_search():
    """Test that perform_sync of sync_enterprise_search pull documents from the queue and index it to the \
         Enterprise Search."""
    indexer_obj = create_enterprise_search_obj()
    indexer_obj.index_documents = Mock(return_value=True)
    indexer_obj.perform_sync()
    assert indexer_obj.queue.empty()
