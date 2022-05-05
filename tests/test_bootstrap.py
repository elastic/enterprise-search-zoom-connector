#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import argparse
import os
import sys
from unittest.mock import Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.bootstrap_command import BootstrapCommand  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def test_execute(caplog):
    """Test execute method in Bootstrap file creates a content source in the Enterprise Search."""
    args = argparse.Namespace()
    args.name = "dummy"
    args.config_file = CONFIG_FILE
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    bootstrap_obj = BootstrapCommand(args)
    bootstrap_obj.config._Configuration__configurations[
        "enterprise_search.host_url"
    ] = "dummy"
    bootstrap_obj.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )
    bootstrap_obj.execute()
    body = {
        "name": args.name,
        "schema": {
            "title": "text",
            "body": "text",
            "url": "text",
            "created_at": "date",
            "name": "text",
            "description": "text",
            "type": "text",
            "size": "text",
        },
        "display": {
           "title_field": "title",
            "description_field": "description",
            "url_field": "url",
            "detail_fields": [
                {"field_name": "created_at", "label": "Created At"},
                {"field_name": "type", "label": "Type"},
                {"field_name": "size", "label": "Size (in bytes)"},
                {"field_name": "description", "label": "Description"},
                {"field_name": "body", "label": "Content"},
            ],
            "color": "#000000",
        },
        "is_searchable": True,
    }
    bootstrap_obj.workplace_search_client.create_content_source.assert_called_with(
        body=body
    )
