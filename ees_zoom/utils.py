#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains un-categorized utility methods.
"""
import time
import urllib.parse
from datetime import datetime

import ruamel.yaml
from tika import parser

from .constant import RFC_3339_DATETIME_FORMAT


class RetryCountExceededException(Exception):
    """Exception raised when retry for api call exceeds.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Retry Count Exceeded while fetching data from Zoom."):
        super().__init__(message)


def extract(content):
    """Extracts the contents
    :param content: content to be extracted
    Returns:
        parsed_test: parsed text
    """
    parsed = parser.from_buffer(content)
    parsed_text = parsed["content"]
    return parsed_text


def url_encode(object_name):
    """Performs encoding on the name of objects
    containing special characters in their url, and
    replaces single quote with two single quote since quote
    is treated as an escape character in odata
    :param object_name: name that contains special characters
    """
    name = urllib.parse.quote(object_name, safe="'")
    return name.replace("'", "''")


def retry(exception_list):
    """Decorator for retrying in case of server exceptions.
    Retries the wrapped method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param exception_list: Lists of exceptions on which the connector should retry
    """

    def decorator(func):
        """This function used as a decorator."""

        def execute(self, *args, **kwargs):
            """This function execute the retry logic."""
            retry = 1
            while retry <= self.retry_count:
                try:
                    return func(self, *args, **kwargs)
                except exception_list as exception:
                    self.logger.exception(
                        f"Error while creating a connection. Retry count: {retry} out of {self.retry_count}. \
                            Error: {exception}"
                    )
                    time.sleep(2**retry)
                    retry += 1
            if retry > self.retry_count:
                raise RetryCountExceededException

        return execute

    return decorator


def split_list_into_buckets(documents, total_buckets):
    """Divide large number of documents amongst the total buckets
    :param documents: list to be partitioned
    :param total_buckets: number of buckets to be formed
    """
    if documents:
        groups = min(total_buckets, len(documents))
        group_list = []
        for i in range(groups):
            group_list.append(documents[i::groups])
        return group_list
    else:
        return []


def split_documents_into_equal_chunks(documents, chunk_size):
    """This method splits a list or dictionary into equal chunks size
    :param documents: List or Dictionary to be partitioned into chunks
    :param chunk_size: Maximum size of a chunk
    Returns:
        list_of_chunks: List containing the chunks
    """
    list_of_chunks = []
    for i in range(0, len(documents), chunk_size):
        if type(documents) is dict:
            partitioned_chunk = list(documents.items())[i:i + chunk_size]
            list_of_chunks.append(dict(partitioned_chunk))
        else:
            list_of_chunks.append(documents[i:i + chunk_size])
    return list_of_chunks


def get_current_time():
    """Returns current time in rfc 3339 format"""
    return (datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT)


def update_yml(config_file_path, config_field_name, refresh_token):
    """Function will update config file with new refresh_token
    :param config_file_path: Path for config_file.
    :param config_field_name: name of config field for which value is updated.
    :param refresh_token: new refresh token.
    """
    yaml = ruamel.yaml.YAML()
    with open(config_file_path, "r", encoding="UTF-8") as file:
        yml_file_data = yaml.load(file)
        yml_file_data.update({config_field_name: f"{refresh_token}"})
    with open(config_file_path, "w", encoding="UTF-8") as file:
        yaml.dump(yml_file_data, file)
