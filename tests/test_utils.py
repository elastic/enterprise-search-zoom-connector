#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.utils import (split_documents_into_equal_chunks,
                            split_list_into_buckets, url_encode)  # noqa


def test_split_list_into_buckets():
    """Test that split_list_into_buckets method divide large number of documents amongst the total buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    total_bucket = 3
    expected_result = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    result = split_list_into_buckets(documents, total_bucket)
    assert result == expected_result


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
