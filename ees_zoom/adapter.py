#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Module containing default schema for data uploaded to Enterprise Search.

    This module contains definition of default schema for the data
    that will be uploaded to Elastic Enterprise Search per the source object.

    Keys for each object represent the fields that will be uploaded to Enterprise Search
    while key values represent the source fields that will be used to populate the data.
"""
DEFAULT_SCHEMA = {
    "users": {
        "created_at": "created_at",
        "id": "id",
        "title": "first_name",
    },
    "channels": {
        "id": "id",
        "title": "name",
    },
    "roles": {
        "description": "description",
        "id": "id",
        "title": "name",
    },
    "meetings": {
        "created_at": "created_at",
        "id": "id",
        "title": "topic",
    },
    "recordings": {
        "created_at": "recording_start",
        "id": "id",
        "size": "total_size",
        "title": "topic",
        "url": "play_url",
    },
    "chats": {
        "created_at": "date_time",
        "description": "message",
        "id": "id",
    },
    "files": {
        "created_at": "date_time",
        "id": "file_id",
        "size": "file_size",
        "title": "file_name",
        "url": "download_url",
    },
    "past_meetings": {
        "created_at": "start_time",
        "id": "uuid",
        "title": "topic",
    },
}
