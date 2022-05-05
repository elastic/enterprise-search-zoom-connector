#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import os
import sys

import ruamel.yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.utils import (split_documents_into_equal_chunks,  # noqa
                            split_list_into_buckets, url_encode, update_yml) # noqa

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def test_split_list_into_buckets():
    """Test that divide large number of documents amongst the total buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 10]
    total_bucket = 3
    target_list = split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count
    assert total_bucket == len(target_list)


def test_split_list_into_buckets_for_duplicate_values():
    """Test that divide large number of documents amongst the total buckets for duplicate values."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 4, 1, 3, 3, 2]
    total_bucket = 3
    target_list = split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count
    assert total_bucket == len(target_list)


def test_split_list_into_buckets_for_uneven_bucket():
    """Test that divide large number of documents amongst the total uneven buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 1, 4, 1]
    total_bucket = 3
    target_list = split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count
    assert total_bucket == len(target_list)


def test_url_encode():
    """Tests url_encode performs encoding on the name of objects"""
    url_to_encode = '''http://ascii.cl?parameter="Click on 'URL Decode'!"'''
    result = url_encode(url_to_encode)
    encoded_url = (
        "http%3A%2F%2Fascii.cl%3Fparameter%3D%22Click%20on%20''URL%20Decode''%21%22"
    )
    assert result == encoded_url


def test_split_documents_into_equal_chunks():
    """Tests split_documents_into_equal_chunks splits a list or dictionary into equal chunks size"""
    list_to_split = ["1", "3", "4", "6", "7", "5", "8", "9", "2", "0", "111"]
    chunk_size = 3
    expected_result = [["1", "3", "4"], ["6", "7", "5"], ["8", "9", "2"], ["0", "111"]]
    result = split_documents_into_equal_chunks(list_to_split, chunk_size)
    assert expected_result == result


def test_update_yml():
    """Tests updating mechanism of yml file."""
    refresh_token = "dummy_refresh_token"
    yaml = ruamel.yaml.YAML()
    with open(CONFIG_FILE, "r", encoding="UTF-8") as file:
        yml_file_data_before_updation = yaml.load(file)

    update_yml(CONFIG_FILE, "zoom.refresh_token", refresh_token)

    with open(CONFIG_FILE, "r", encoding="UTF-8") as file:
        yml_file_data_after_updation = yaml.load(file)

    for key, value_before_updation in yml_file_data_before_updation.items():
        if key != "zoom.refresh_token":
            assert value_before_updation == yml_file_data_after_updation[key]
        else:
            assert refresh_token == yml_file_data_after_updation[key]
            update_yml(CONFIG_FILE, "zoom.refresh_token", value_before_updation)