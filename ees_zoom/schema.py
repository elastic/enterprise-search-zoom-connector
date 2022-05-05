#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""schema module contains Connector configuration file schema.
"""
import datetime

from .constant import RFC_3339_DATETIME_FORMAT


def coerce_rfc_3339_date(input_date):
    """This function returns true if its argument is a valid RFC 3339 date."""
    if input_date:
        return datetime.datetime.strptime(input_date, RFC_3339_DATETIME_FORMAT)
    return False


schema = {
    "zoom.client_id": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "zoom.client_secret": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "zoom.refresh_token": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "enterprise_search.api_key": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "enterprise_search.source_id": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "enterprise_search.host_url": {
        "required": True,
        "type": "string",
        "empty": False,
    },
    "enable_document_permission": {
        "required": False,
        "type": "boolean",
        "default": True,
    },
    "objects": {
        "type": "dict",
        "nullable": True,
        "schema": {
            "users": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "channels": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "roles": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "meetings": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "recordings": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "chats": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "files": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "past_meetings": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
            "groups": {
                "type": "dict",
                "nullable": True,
                "schema": {
                    "include_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                    "exclude_fields": {
                        "nullable": True,
                        "type": "list",
                    },
                },
            },
        },
    },
    "start_time": {
        "required": False,
        "type": "datetime",
        "max": datetime.datetime.utcnow(),
        "default": "2011-10-12T00:00:00Z",  # Zoom Creation Date
        "coerce": coerce_rfc_3339_date,
    },
    "end_time": {
        "required": False,
        "type": "datetime",
        "max": datetime.datetime.utcnow(),
        "default": (datetime.datetime.utcnow()).strftime(RFC_3339_DATETIME_FORMAT),
        "coerce": coerce_rfc_3339_date,
    },
    "log_level": {
        "required": False,
        "type": "string",
        "default": "INFO",
        "allowed": ["DEBUG", "INFO", "WARN", "ERROR"],
    },
    "retry_count": {
        "required": False,
        "type": "integer",
        "default": 3,
        "min": 1,
    },
    "zoom_sync_thread_count": {
        "required": False,
        "type": "integer",
        "default": 5,
        "min": 1,
    },
    "enterprise_search_sync_thread_count": {
        "required": False,
        "type": "integer",
        "default": 5,
        "min": 1,
    },
    "zoom.user_mapping": {
        "required": False,
        "type": "string",
    },
}
