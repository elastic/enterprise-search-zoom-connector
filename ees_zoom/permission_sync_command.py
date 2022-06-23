#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a permission sync against the source instance.

    It will attempt to remove from Enterprise Search instance the documents
    that have been deleted from the third-party system.
"""
import os

from .base_command import BaseCommand
from .zoom_roles import ZoomRoles


class PermissionSyncDisabledException(Exception):
    """Exception raised when permission sync is disabled, but expected to be enabled.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="The Permission flag is disabled"):
        super().__init__(message)


class EmptyMappingException(Exception):
    """Exception raised when mapping file is not present or empty and the sync_user_permissions
        is executed.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Mapping not found"):
        super().__init__(message)


class PermissionSyncCommand(BaseCommand):
    """This class contains logic to sync user permissions from the source.

    It can be used to run the job that will periodically sync permissions
    from the source to Elastic Enterprise Search."""

    def __init__(self, args):
        super().__init__(args)

        config = self.config

        self.logger.debug("Initializing the Permission Indexing class")
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.enable_document_permission = config.get_value("enable_document_permission")
        self.user_mapping = config.get_value("zoom.user_mapping")

    def remove_all_permissions(self):
        """Removes all the permissions present in the workplace"""
        try:
            user_permission = self.workplace_search_client.list_permissions()
            if user_permission:
                self.logger.info("Removing the permissions from the workplace...")
                permission_list = user_permission["results"]
                for permission in permission_list:
                    self.workplace_search_client.remove_permissions(permission)
        except ValueError as error:
            raise error
        except Exception as exception:
            self.logger.exception(
                f"Error while removing the permissions from the workplace. Error: {exception}"
            )
            raise exception

    def set_permissions_list(self, mappings):
        """Method fetches roles and its members from zoom along with list of permissions associated with each
        role and adds fetched permissions to enterprise search users.
        :param mappings: Zoom-Enterprise search mapping dictionary
        """
        roles_obj = ZoomRoles(self.config, self.logger, self.zoom_client, mappings)
        roles_obj.set_list_of_roles_from_zoom()
        for role in roles_obj.roles_list:
            role_permissions = roles_obj.fetch_role_permissions(role["id"])
            role_members_ids = roles_obj.fetch_members_of_role(role["id"])
            for zoom_user, enterprise_search_users in mappings.items():
                if zoom_user in role_members_ids:
                    for enterprise_search_user in enterprise_search_users:
                        role_permissions.append(enterprise_search_user)
                        self.workplace_search_client.add_permissions(
                            enterprise_search_user, role_permissions
                        )

    def execute(self):
        """Runs the permission indexing logic.

        This method when invoked, checks the permission of the source users and update those user
        permissions in the Workplace Search.
        """
        self.logger.info("Starting the permission indexing..")
        self.zoom_client.get_token()
        if not self.enable_document_permission:
            self.logger.warning("Exiting as the enable permission flag is set to False")
            raise PermissionSyncDisabledException
        if (
            self.user_mapping and os.path.exists(self.user_mapping) and os.path.getsize(self.user_mapping) > 0
        ):
            self.remove_all_permissions()
            self.set_permissions_list(self.zoom_enterprise_search_mappings)
        else:
            self.logger.error(
                f"Could not find the users mapping file at the location: {self.user_mapping} or the file is empty. \
                Please add the source_user->enterprise_search_user mappings to sync the permissions in the \
                    Enterprise Search"
            )
            raise EmptyMappingException
