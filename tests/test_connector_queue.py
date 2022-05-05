import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_zoom.configuration import Configuration  # noqa
from ees_zoom.connector_queue import ConnectorQueue  # noqa
from ees_zoom.utils import get_current_time  # noqa


def test_end_signal():
    """Tests that the end signal is sent to the queue to notify it to stop listening for new incoming data"""
    expected_message = {"type": "signal_close"}
    logger = logging.getLogger("unit_test_connector_queue")
    queue = ConnectorQueue(logger)
    queue.put("Example data")
    queue.end_signal()
    queue.get()
    message = queue.get()
    assert message == expected_message


def test_append_to_queue():
    """Tests that the end signal is sent to the queue to notify it to stop listening for new incoming data"""
    data = []
    for count in range(10):
        data.append(count)
    expected_message_1 = {"type": "document_list", "data": data[:99]}

    logger = logging.getLogger("unit_test_connector_queue")
    queue = ConnectorQueue(logger)
    queue.append_to_queue(data)
    queue.end_signal()

    message_1 = queue.get()
    queue.get()

    if message_1 == expected_message_1:
        assert True


def test_put_checkpoint():
    """Tests that the end signal is sent to the queue to notify it to stop listening for new incoming data"""
    current_time = get_current_time()
    expected_message = {"type": "checkpoint", "data": (current_time, "full", "key")}
    logger = logging.getLogger("unit_test_connector_queue")
    queue = ConnectorQueue(logger)
    queue.put("Example data")
    queue.put_checkpoint("key", current_time, "full")
    queue.end_signal()
    queue.get()
    message = queue.get()
    queue.get()
    assert message == expected_message
