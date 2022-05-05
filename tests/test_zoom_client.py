import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.utils import update_yml  # noqa 
from ees_zoom.zoom_client import ZoomClient  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "zoom_connector.yml",
)


def settings():
    """This function loads configuration from the file and initialize logger.
    :returns configuration: Configuration instance
    :returns logger: Logger instance
    """
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_zoom_client")
    return configuration, logger


def get_zoom_client_object(configs, logger):
    """return Zoom client's object

    :param configs : Configuration class object
    :param logger: Logger object.
    :returns ZoomClient: Instance of ZoomClient.
    """
    return ZoomClient(configs, logger)


def test_get_token(requests_mock):
    """Test for get_token function call
    :param requests_mock: fixture for mocking requests calls.
    """
    new_refresh_token = "new_dummy_refresh_token"
    access_token = "dummy_access_token"
    json_response = {"refresh_token": new_refresh_token, "access_token": access_token}
    config, logger = settings()
    old_refresh_token = config.get_value("zoom.refresh_token")
    zoom_client_object = get_zoom_client_object(config, logger)
    refresh_token_from_config_file = zoom_client_object.refresh_token
    url = f"""https://zoom.us/oauth/token?refresh_token={refresh_token_from_config_file}&grant_type=refresh_token"""
    headers = zoom_client_object.get_headers()
    requests_mock.post(
        url,
        headers=headers,
        json=json_response,
        status_code=200,
    )
    zoom_client_object.get_token()
    assert zoom_client_object.access_token == access_token
    new_config, _ = settings()
    new_refresh_token_from_new_config = new_config.get_value("zoom.refresh_token")
    assert new_refresh_token_from_new_config == new_refresh_token
    update_yml(CONFIG_FILE, "zoom.refresh_token", old_refresh_token)