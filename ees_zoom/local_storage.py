#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import json
import os

IDS_PATH = os.path.join(os.path.dirname(__file__), "doc_id.json")


class LocalStorage:
    """This class contains all the methods to perform operations on doc_id.json file.

    The doc_id.json file is a local storage that the connector uses to track the identifiers(IDs) of the documents
    that were successfully indexed to the Enterprise Search.
    This storage is then traversed during the deletion sync to validate if any of these indexed documents have been
    later deleted from the source, if so, the deletion sync will delete those documents from the Enterprise Search.

    The structure of the doc_id.json is {'global_keys': [], 'delete_keys':[]}:
        - global_keys: Stores all the document ids that are successfully indexed and present in the Enterprise Search.
        - delete_keys: Store all the document ids that are NOT recently updated, so the deletion sync
          would just check if those not recently updated documents are present anymore in the source

    Use this class to perform read/write operations to the doc_id.json file(Local Storage)
    """

    def __init__(self, logger):
        self.logger = logger

    def load_storage(self):
        """This method fetches the contents of doc_id.json(local ids storage)"""
        try:
            with open(IDS_PATH, encoding="utf-8") as ids_file:
                try:
                    return json.load(ids_file)
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the json file of the ids store from path: {IDS_PATH}. Error: {exception}"
                    )
        except FileNotFoundError:
            self.logger.debug("Local storage for ids was not found.")
            return {"global_keys": []}

    def update_storage(self, ids):
        """This method is used to update the ids stored in doc_id.json file
        :param ids: updated ids to be stored in the doc_id.json file
        """
        with open(IDS_PATH, "w", encoding="utf-8") as ids_file:
            try:
                json.dump(ids, ids_file, indent=4)
            except ValueError as exception:
                self.logger.exception(f"Error while updating the doc_id json file. Error: {exception}")
