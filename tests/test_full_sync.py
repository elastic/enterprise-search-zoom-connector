#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
from unittest.mock import MagicMock, Mock, patch

from ees_zoom.configuration import Configuration
from ees_zoom.connector_queue import ConnectorQueue
from ees_zoom.full_sync_command import FullSyncCommand
from ees_zoom.sync_zoom import SyncZoom
from support import get_args


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""

    configuration = Configuration(
        file_name=os.path.join(
            os.path.join(os.path.dirname(__file__), "config"),
            "zoom_connector.yml",
        )
    )
    logger = logging.getLogger("unit_test_full_sync")
    return configuration, logger


@patch.object(SyncZoom, "perform_sync")
@patch.object(SyncZoom, "get_all_users_from_zoom")
def test_start_producer(mock1, mock2):
    """Test method of start producer to fetching data from outlook for full sync
    :param mock1: patch for get_all_users_from_zoom
    :param mock2: patch for perform_sync
    """
    config, logger = settings()
    args = get_args("FullSyncCommand")
    full = FullSyncCommand(args)
    queue = ConnectorQueue(logger)
    mock1.return_value = [MagicMock()]
    full.create_and_execute_jobs = Mock()
    full.create_and_execute_jobs.return_value = MagicMock()
    full.zoom_client.get_token = Mock()
    mock2.return_value = MagicMock()
    full.start_producer(queue)
    time_independent_objects = ["roles", "groups"]
    object_types_count = 0
    object_types_count = sum(
        object not in time_independent_objects for object in config.get_value("objects")
    )
    total_expected_size = object_types_count + config.get_value(
        "enterprise_search_sync_thread_count"
    )
    assert queue.qsize() == total_expected_size
    queue.close()
    queue.join_thread()
