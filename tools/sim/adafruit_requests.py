"""Stand-in for adafruit_requests: answers every GET with the example summary of the home hub."""
import json
import os

SAMPLE = os.path.join(os.path.dirname(__file__), "hub_beispiel.json")


class _Response:
    status_code = 200

    def json(self):
        with open(SAMPLE) as f:
            return json.load(f)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Session:
    def __init__(self, pool, ssl_context=None):
        pass

    def get(self, url, headers=None, timeout=None):
        return _Response()
