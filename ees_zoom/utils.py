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

import tika
from requests.exceptions import ReadTimeout
from tika import parser
from urllib3.exceptions import ReadTimeoutError

from .constant import RFC_3339_DATETIME_FORMAT

TIKA_TIMEOUT = 60  # Timeout in seconds


class RetryCountExceededException(Exception):
    """Exception raised when retry for api call exceeds.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Retry Count Exceeded while fetching data from Zoom."):
        super().__init__(message)


def extract(content, document_name, logger, retry_count):
    """Extracts the contents
    :param content: content to be extracted
    Returns:
        parsed_test: parsed text
    """
    while retry_count:
        try:
            parsed = parser.from_buffer(
                content, requestOptions={"timeout": TIKA_TIMEOUT}
            )
            return parsed["content"]
        except (ReadTimeoutError, ReadTimeout):
            logger.error(
                f"Tika timeout while parsing the content for {document_name}. Retrying.."
            )
        except (ConnectionError, RuntimeError):
            logger.error("Could not reach Tika server. Retrying...")
            tika.initVM()
        finally:
            retry_count -= 1
    return ""


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


def split_by_max_cumulative_length(documents, allowed_size):
    """This method splits a list or dictionary into list based on allowed size limit.
    :param documents: List or Dictionary to be partitioned into chunks
    :param allowed_size: Maximum size allowed for indexing per request.
    Returns:
        list_of_chunks: List of list of dictionary containing the dictionaries to be indexed.
    """
    list_of_chunks = []
    chunk = []
    current_size = allowed_size
    for document in documents:
        document_size = len(str(document))
        if document_size < current_size:
            chunk.append(document)
            current_size -= document_size
        else:
            if chunk:
                list_of_chunks.append(chunk)
            if document_size > allowed_size:
                document["body"] = None
                document_size = len(str(document))
            chunk = [document]
            current_size = allowed_size - document_size
    list_of_chunks.append(chunk)
    return list_of_chunks


def get_current_time():
    """Returns current time in rfc 3339 format"""
    return (datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT)


def is_within_time_range(document, time_range):
    """Check if document is created within time range or not.
    :param document: dictionary of document from doc_id.json delete_keys.
    :param time_range: datetime object limit for given document type(ex: one_month_ago or six_months_ago).
    :returns: boolean to check if document is created within time range or not.
    """
    return (
        datetime.strptime(document["created_at"], RFC_3339_DATETIME_FORMAT) < time_range
    )


def constraint_time_range(start_time, end_time, time_constraint, logger):
    """Constraint the time range(i.e. start time and end time) based on the time_constraint passed.
    If the start time or end time is before the allowed time constraint, then default the time range
    according to the allowed time constraint)
    :param start_time: datetime object for lower limit for data fetching.
    :param end_time: datetime object for upper limit for data fetching.
    :param time_constraint: datetime object containing the lower-bound for time-range.
    :param logger: Logger object.
    :returns: updated datetime string for start time and end time.
    """
    if start_time < time_constraint:
        logger.warning(
            f"Start time is lesser than the allowed limit. Expected allowed limit : {time_constraint}"
            f" and found: {start_time}.\nSetting the start time to : {time_constraint}"
        )
        start_time = time_constraint
    if end_time < time_constraint:
        logger.warning(
            f"End time is lesser than the allowed limit. Expected allowed limit : {time_constraint}"
            f" and found: {end_time}.\nSetting the end time to : {datetime.utcnow()}"
        )
        end_time = datetime.utcnow()
    start_time = start_time.strftime(RFC_3339_DATETIME_FORMAT)
    end_time = end_time.strftime(RFC_3339_DATETIME_FORMAT)
    return start_time, end_time
