"""pact test for a message consumer"""

import logging
import pytest
import time

from os import remove
from os.path import isfile

from pact import MessageConsumer, Provider
from src.message_handler import MessageHandler, CustomError

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PACT_BROKER_URL = "http://localhost"
PACT_BROKER_USERNAME = "pactbroker"
PACT_BROKER_PASSWORD = "pactbroker"
PACT_DIR = 'pacts'

CONSUMER_NAME = 'DetectContentLambda'
PROVIDER_NAME = 'ContentProvider'
PACT_FILE = (f"{CONSUMER_NAME.lower().replace(' ', '_')}_message-"
             + f"{PROVIDER_NAME.lower().replace(' ', '_')}_message.json")

@pytest.fixture(scope='session')
def pact(request):
    version = request.config.getoption('--publish-pact')
    publish = True if version else False

    pact = MessageConsumer(CONSUMER_NAME, version=version).has_pact_with(
        Provider(PROVIDER_NAME),
        publish_to_broker=publish, broker_base_url=PACT_BROKER_URL,
        broker_username=PACT_BROKER_USERNAME, broker_password=PACT_BROKER_PASSWORD)

    # current pact does not consider the PACT_DIR argument, assumes none
    yield pact


def cleanup_json(file):
    """
    Remove existing json file before test if any
    """
    if (isfile(f"{file}")):
        remove(f"{file}")


def progressive_delay(file, time_to_wait=10, second_interval=0.5, verbose=False):
    """
    progressive delay
    defaults to wait up to 5 seconds with 0.5 second intervals
    """
    time_counter = 0
    while not isfile(file):
        time.sleep(second_interval)
        time_counter += 1
        if verbose:
            print(f'Trying for {time_counter*second_interval} seconds')
        if time_counter > time_to_wait:
            if verbose:
                print(f'Already waited {time_counter*second_interval} seconds')
            break


def test_throw_exception_handler(pact):
    cleanup_json(PACT_FILE)
    wrong_event = {
        'documentName': 'spreadsheet.xls',
        'creator': 'WI',
        'documentType': 'microsoft-excel'
    }

    (pact
     .given('Another document in Document Service')
     .expects_to_receive('Description')
     .with_content(wrong_event)
     .with_metadata({
         'Content-Type': 'application/json'
     }))

    with pytest.raises(CustomError):
        with pact:
            # handler needs 'documentType' == 'microsoft-word'
            MessageHandler(wrong_event)

    progressive_delay(f"{PACT_FILE}")
    assert isfile(f"{PACT_FILE}") == 0


def test_generate_new_pact_file(pact):
    cleanup_json(PACT_FILE)

    expected_event = {
        'documentName': 'document.doc',
        'creator': 'TP',
        'documentType': 'microsoft-word'
    }

    (pact
     .given('A document create in Document Service')
     .expects_to_receive('Description')
     .with_content(expected_event)
     .with_metadata({
         'Content-Type': 'application/json'
     }))

    with pact:
        # handler needs 'documentType' == 'microsoft-word'
        MessageHandler(expected_event)

    progressive_delay(f"{PACT_FILE}")
    assert isfile(f"{PACT_FILE}") == 1


def test_publish_to_broker(pact):
    """
    This test does not clean-up previously generated pact.
    Sample execution where 2 is an arbitrary version:

    `pytest tests/consumer/test_message_consumer.py::test_publish_pact_to_broker`

    `pytest tests/consumer/test_message_consumer.py::test_publish_pact_to_broker --publish-pact 2`
    """
    expected_event = {
        'documentName': 'document.doc',
        'creator': 'TP',
        'documentType': 'microsoft-word'
    }

    (pact
     .given('A document create in Document Service with broker')
     .expects_to_receive('Description with broker')
     .with_content(expected_event)
     .with_metadata({
         'Content-Type': 'application/json'
     }))

    with pact:
        MessageHandler(expected_event)

    progressive_delay(f"{PACT_FILE}")
    assert isfile(f"{PACT_FILE}") == 1
