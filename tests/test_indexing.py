#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
from unittest.mock import MagicMock, Mock

import pytest
from elastic_enterprise_search import __version__
from packaging import version

if version.parse(__version__) >= version.parse("8.0"):
    from elastic_enterprise_search.exceptions import BadGatewayError
else:
    from elastic_transport.exceptions import BadGatewayError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.connector_queue import ConnectorQueue  # noqa
from ees_zoom.enterprise_search_wrapper import EnterpriseSearchWrapper  # noqa
from ees_zoom.sync_enterprise_search import SyncEnterpriseSearch  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_indexing")
    return configuration, logger


def create_enterprise_search_object():
    """This function create Enterprise Search object for test."""
    configs, logger = settings()
    args = argparse.Namespace()
    workplace_search_client = EnterpriseSearchWrapper(logger, configs, args)
    queue = ConnectorQueue(logger)
    queue.end_signal()
    return SyncEnterpriseSearch(configs, logger, workplace_search_client, queue)


@pytest.mark.parametrize(
    "documents, mock_response",
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
        )
    ],
)
def test_index_document(documents, mock_response, caplog):
    """Test that index_document successfully index documents in Enterprise Search.
    :param documents: generated document.
    :param mock_response: mocked returned response
    :param caplog: records the attributes from current stage.
    """
    # Setup
    caplog.set_level("INFO")
    indexer_object = create_enterprise_search_object()
    indexer_object.workplace_search_client.index_documents = Mock(
        return_value=mock_response
    )

    # Execute
    indexer_object.index_documents(documents)

    # Assert
    assert indexer_object.total_document_indexed == 2

    # Cleanup
    indexer_object.queue.close()
    indexer_object.queue.join_thread()


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
    """Test that index_document give proper error message if document not indexed.
    :param documents: Generated document ready to be indexed.
    :param mock_response: Mocker response object
    :param log_msg: Log message to display.
    :param caplog: Pytest logging object.
    """
    # Setup
    caplog.set_level(log_level)
    indexer_object = create_enterprise_search_object()
    indexer_object.workplace_search_client.index_documents = Mock(
        return_value=mock_response
    )

    # Execute
    indexer_object.index_documents(documents)

    # Assert
    assert error_msg in caplog.text

    # Cleanup
    indexer_object.queue.close()
    indexer_object.queue.join_thread()


def test_perform_sync_enterprise_search():
    """Test that perform_sync of sync_enterprise_search pull documents from the queue and index it to the \
         Enterprise Search."""
    # Setup
    indexer_object = create_enterprise_search_object()
    indexer_object.index_documents = Mock(return_value=True)

    # Execute
    indexer_object.perform_sync()

    # Assert
    assert indexer_object.queue.empty()

    # Cleanup
    indexer_object.queue.close()
    indexer_object.queue.join_thread()


def test_index_document_negative():
    """Test that index_document retries for BadGateway and Timeout exception."""
    # Setup
    dummy_documents_to_index = [
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
    ]
    indexer_object = create_enterprise_search_object()
    mock_response = [Mock(), Mock(), Mock()]
    if version.parse(__version__) >= version.parse("8.0"):
        mock_response[0] = BadGatewayError(
            meta=Mock(status=502),
            message="Connection Reset By peer",
            body="Connection reset reason",
        )
        mock_response[1] = BadGatewayError(
            meta=Mock(status=502),
            message="Connection Reset By peer",
            body="Connection reset reason",
        )
    else:
        mock_response[0] = BadGatewayError(message="Connection Reset By peer")
        mock_response[1] = BadGatewayError(message="Connection Reset By peer")
    mock_response[2] = {
        "results": [{"id": "0", "errors": []}, {"id": "1", "errors": []}]
    }
    indexer_object.workplace_search_client.workplace_search_client.index_documents = (
        MagicMock()
    )
    indexer_object.workplace_search_client.workplace_search_client.index_documents.side_effect = (
        mock_response
    )
    timeout = 60

    # Execute
    indexer_object.workplace_search_client.index_documents(
        dummy_documents_to_index, timeout
    )

    # Assert
    assert (
        3
        == indexer_object.workplace_search_client.workplace_search_client.index_documents.call_count
    )


def test_index_document_positive():
    """Test that index_document successfully index documents in Enterprise Search."""
    # Setup
    dummy_documents_to_index = [
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
    ]
    indexer_object = create_enterprise_search_object()
    mock_response = [Mock()]
    mock_response[0] = {
        "results": [{"id": "0", "errors": []}, {"id": "1", "errors": []}]
    }
    indexer_object.workplace_search_client.workplace_search_client.index_documents = (
        MagicMock()
    )
    indexer_object.workplace_search_client.workplace_search_client.index_documents.side_effect = (
        mock_response
    )
    timeout = 60

    # Execute
    indexer_object.workplace_search_client.index_documents(
        dummy_documents_to_index, timeout
    )

    # Assert
    assert 1 == indexer_object.workplace_search_client.workplace_search_client.index_documents.call_count

    # Cleanup
    indexer_object.queue.close()
    indexer_object.queue.join_thread()
