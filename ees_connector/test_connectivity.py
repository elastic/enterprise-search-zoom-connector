#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""test_connectivity module allows to test that connector setup is correct.

It's possible to check connectivity to the source instance,
to Elastic Enterprise Search instance and check if ingestion of
documents works."""

import logging
import time

import pytest
from elastic_enterprise_search import WorkplaceSearch

from .configuration import Configuration


@pytest.fixture(name="settings")
def fixture_settings():
    """This function loads config from the file and returns it along with retry_count setting."""
    configuration = Configuration(file_name="config.yml")

    logger = logging.getLogger("test_connectivity")
    return configuration, logger


@pytest.mark.enterprise_search
def test_workplace(settings):
    """Tests the connection to the Enterprise search host"""
    configs, _ = settings
    print("Starting Enterprise Search connectivity tests..")
    retry_count = configs.get_value("retry_count")
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    retry = 0
    while retry <= retry_count:
        try:
            workplace_search = WorkplaceSearch(
                enterprise_search_host,
                http_auth=configs.get_value("enterprise_search.api_key"),
            )
            response = workplace_search.get_content_source(
                content_source_id=configs.get_value("enterprise_search.source_id")
            )
            if response:
                assert True
                break
        except Exception as exception:
            print(
                f"[Fail] Error while connecting to the Enterprise Search host {enterprise_search_host}. \
                    Retry Count: {retry}. Error: {exception}"
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2**retry)
            else:
                assert False, f"Error while connecting to the Enterprise Search at {enterprise_search_host}"
            retry += 1

    print("Enterprise Search connectivity tests completed..")


@pytest.mark.ingestion
def test_ingestion(settings):
    """Tests the successful ingestion and deletion of a sample document to the Enterprise search"""
    configs, logger = settings
    retry_count = configs.get_value("retry_count")
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    print("Starting Enterprise Search ingestion tests..")
    document = [
        {
            "id": 1234,
            "title": "The Meaning of Time",
            "body": "Not much. It is a made up thing.",
            "url": "https://example.com/meaning/of/time",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "list",
        }
    ]
    workplace_search = WorkplaceSearch(enterprise_search_host)
    retry = 0
    response = None
    while retry <= retry_count:
        try:
            response = workplace_search.index_documents(
                http_auth=configs.get_value("enterprise_search.api_key"),
                content_source_id=configs.get_value("enterprise_search.source_id"),
                documents=document,
            )
            print("Successfully indexed a dummy document with id 1234 to the Enterprise Search")
            break
        except Exception as exception:
            print(
                f"[Fail] Error while ingesting document to the Enterprise Search host {enterprise_search_host}. \
                Retry Count: {retry}. Error: {exception}"
            )
            # This condition is to avoid sleeping for the last time
            if retry < retry_count:
                time.sleep(2**retry)
            else:
                assert False, f"Error while connecting to the Enterprise Search at {enterprise_search_host}"
            retry += 1

    if response:
        print("Attempting to delete the dummy document 1234 from the Enterprise Search for cleanup")
        retry = 0
        while retry <= retry_count:
            try:
                response = workplace_search.delete_documents(
                    http_auth=configs.get_value("enterprise_search.api_key"),
                    content_source_id=configs.get_value("enterprise_search.source_id"),
                    document_ids=[1234],
                )
                print("Successfully deleted the dummy document with id 1234 from the Enterprise Search")
                if response:
                    assert True
                    break
            except Exception as exception:
                print(
                    f"[Fail] Error while deleting document id 1234 from the Enterprise Search host {enterprise_search_host}. \
                        Retry Count: {retry}. Error: {exception}"
                )
                # This condition is to avoid sleeping for the last time
                if retry < retry_count:
                    time.sleep(2**retry)
                else:
                    assert False, "Error while connecting to the Enterprise Search at {enterprise_search_host}"
                retry += 1

    print("Enterprise Search ingestion tests completed..")
