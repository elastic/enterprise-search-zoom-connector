#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import datetime
import json
import logging
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.checkpointing import Checkpoint  # noqa
from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.constant import RFC_3339_DATETIME_FORMAT  # noqa

CHECKPOINT_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "ees_zoom",
    "checkpoint.json",
)


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(
        os.path.join(
            os.path.join(os.path.dirname(__file__), "config"),
            "zoom_connector.yml",
        )
    )

    logger = logging.getLogger("unit_test_checkpointing")
    return configuration, logger


def test_set_checkpoint_when_checkpoint_file_available():
    """Test set current time in checkpoint.json file when checkpoint.json file is available."""
    configs, logger = settings()
    checkpoint_obj = Checkpoint(configs, logger)
    current_time = datetime.datetime.utcnow()
    current_time_strf = (current_time).strftime(RFC_3339_DATETIME_FORMAT)
    dummy_object_type = {"dummy": (current_time).strftime(RFC_3339_DATETIME_FORMAT)}
    with open(CHECKPOINT_PATH, "w", encoding="UTF-8") as outfile:
        json.dump(dummy_object_type, outfile, indent=4)
    checkpoint_obj.set_checkpoint(current_time_strf, "incremental", "dummy")
    with open(CHECKPOINT_PATH, encoding="UTF-8") as checkpoint_store:
        checkpoint_list = json.load(checkpoint_store)
    assert checkpoint_list["dummy"] == current_time_strf


@pytest.mark.parametrize(
    "index_type, expected_time, current_time, obj_type",
    [
        (
            "incremental",
            "2021-12-28T15:14:28Z",
            (datetime.datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT),
            "dummy",
        ),
        (
            "full_sync",
            (datetime.datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT),
            (datetime.datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT),
            "dummy",
        ),
    ],
)
def test_set_checkpoint_when_checkpoint_file_not_available(
    index_type, expected_time, current_time, obj_type
):
    """Test set correct time in checkpoint.json file when checkpoint.json file is not available.
    :param index_type: Incremental or Full-sync Indexing.
    :param expected_time: expected time value when checkpoint file is not available.
    :param obj_type: object name for which checkpoint will be fetch.
    """
    configs, logger = settings()
    checkpoint_obj = Checkpoint(configs, logger)
    checkpoint_obj.config._Configuration__configurations["end_time"] = expected_time
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    checkpoint_obj.set_checkpoint(current_time, index_type, obj_type)
    with open(CHECKPOINT_PATH, encoding="UTF-8") as checkpoint_store:
        checkpoint_list = json.load(checkpoint_store)
    assert checkpoint_list[obj_type] == expected_time


def test_get_checkpoint_when_checkpoint_file_available():
    """Test that get checkpoint details from checkpoint.json file when checkpoint.json file is available."""
    configs, logger = settings()
    checkpoint_obj = Checkpoint(configs, logger)
    checkpoint_time = (
        datetime.datetime.utcnow() - datetime.timedelta(days=3)
    ).strftime(RFC_3339_DATETIME_FORMAT)
    dummy_object_type = {"dummy": checkpoint_time}
    with open(CHECKPOINT_PATH, "w", encoding="UTF-8") as outfile:
        json.dump(dummy_object_type, outfile, indent=4)
    current_time = (datetime.datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT)
    start_time, end_time = checkpoint_obj.get_checkpoint(current_time, "dummy")
    assert start_time == checkpoint_time
    assert end_time == current_time
