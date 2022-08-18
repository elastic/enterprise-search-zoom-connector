#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

"""zoom_roles module is responsible to get all the available roles from Zoom and
generate documents from fetched responses.
"""

import threading

from .constant import ROLES

CHAT_MESSAGE_READ_PERMISSION = "ChatMessage:Read"


class ZoomRoles:
    """Class is responsible to fetch all roles available in Zoom, creates a list containing these roles and
    generates documents for each role fetched.
    """

    def __init__(
        self, config, logger, zoom_client, zoom_enterprise_search_mappings
    ) -> None:
        self.config = config
        self.logger = logger
        self.zoom_client = zoom_client
        self.zoom_enterprise_search_mappings = zoom_enterprise_search_mappings
        self.roles_list = []
        self.retry_count = config.get_value("retry_count")

    def set_list_of_roles_from_zoom(self):
        """This function will fetch all the available roles from Zoom
        and will partition them in equal groups based on zoom_sync_thread_count
        then store all the roles in object variable.
        """
        try:
            roles_response_list = self.zoom_client.get(end_point=ROLES, key=ROLES)
            self.roles_list.extend(roles_response_list)
        except Exception as exception:
            self.logger.error(
                f"Error occurred while fetching roles from Zoom: {exception}"
            )

    def get_roles_details_documents(
        self,
        roles_schema,
        roles_data,
        enable_permission,
    ):
        """This function will create documents to index in workplace search
        :param roles_schema: dictionary of fields available in Include_fields and DEFAULT_SCHEMA.
        :param roles_data: list of dictionary contains roles data fetched from Zoom api.
        :param enable_permission: boolean to check if permission sync is enabled or not.
        :returns: dictionary containing type of data along with the data.
        """
        try:
            if not roles_data:
                return {"type": ROLES, "data": []}
            roles_count = 0
            roles_documents = []
            for role in roles_data:
                role_document = {"type": ROLES}
                for ws_field, zoom_fields in roles_schema.items():
                    role_document[ws_field] = role[zoom_fields]
                role_document["body"] = f"Total Members : {role['total_members']}"
                role_document[
                    "url"
                ] = f"https://zoom.us/role#/detail/{role['id']}/settings"
                if enable_permission:
                    permission_list = ["Role:Read"]
                    role_document["_allow_permissions"] = permission_list
                roles_documents.append(role_document)
                roles_count += 1
            self.logger.info(
                f"Thread: [{threading.get_ident()}] {roles_count} number(s) of roles documents generated."
            )
            return {"type": ROLES, "data": roles_documents}
        except KeyError as key_error_exception:
            self.logger.error(
                f"Error {key_error_exception} occurred while generating roles documents."
            )
            raise

    def fetch_role_permissions(self, role_id):
        """This function will fetch all the permissions using role id.
        :param role_id: string of the role ID.
        :returns: list of all the permissions enabled for role.
        """
        privileges_of_role = []
        try:
            privileges_of_role = self.zoom_client.get(
                end_point=f"roles/{role_id}", key="privileges"
            )
        except Exception as exception:
            self.logger.error(
                f"Unknown error ocurred while fetching roles permissions from Zoom: {exception}"
            )
        self.logger.info(
            f"Thread: [{threading.get_ident()}] fetched : {len(privileges_of_role)} privileges for role id:{role_id}"
        )
        return privileges_of_role

    def fetch_members_of_role(self, role_id):
        """Function fetches members which have role_id assigned to them.
        :param role_id: string of the role ID for which It has to fetch members.
        :returns: list of member_id having role as role_id.
        """
        users_list = []
        try:
            users_list = self.zoom_client.get(
                end_point=f"roles/{role_id}/members?page_size=300",
                key="members",
                is_paginated=True,
            )
        except Exception as exception:
            self.logger.error(
                f"Unknown error ocurred while fetching members from Zoom: {exception} For role id:{role_id}"
            )
        member_ids = [member["id"] for member in users_list]
        self.logger.info(
            f"Thread: [{threading.get_ident()}] fetched : {len(users_list)} members for role id:{role_id} ."
        )
        return member_ids

    def fetch_user_ids_with_chat_access(self):
        """This method will fetch the userID of users having read access for chat messages.
        :returns: list containing userIDs of users having read access for chat messages.
        """
        self.set_list_of_roles_from_zoom()
        chat_permission_users_list = []
        for role in self.roles_list:
            role_permissions = self.fetch_role_permissions(role["id"])
            role_members_ids = self.fetch_members_of_role(role["id"])
            for role_permission in role_permissions:
                if role_permission == CHAT_MESSAGE_READ_PERMISSION:
                    chat_permission_users_list.extend(role_members_ids)
        return chat_permission_users_list
