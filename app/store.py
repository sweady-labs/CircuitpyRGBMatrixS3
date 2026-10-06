"""Settings, kept as JSON in the NVM of the microcontroller (8 KB, survives restarts and updates).

Only the web interface changes settings. Writes are delayed a little (save_if_due), so dragging
the brightness slider does not write to flash on every step.
"""
import json
import time

MAGIC = b"LM2"
SAVE_DELAY = 3

DEFAULTS = {
    "scene": "uhr",
    "on": True,
    "brightness": 60,
    "playlist": {"on": False, "minutes": 10, "scenes": ["uhr", "plasma", "polarlicht", "feuer", "hub_status"]},
    "night": {"on": False, "start": "22:30", "end": "06:30", "level": 0},
    "message": {"text": "Hallo!", "color": "#FFB000", "speed": 3},
}

_due = None


def _merged(saved):
    """DEFAULTS, overwritten by what was saved (new keys from DEFAULTS survive updates)."""
    result = {}
    for key, value in DEFAULTS.items():
        if isinstance(value, dict):
            result[key] = dict(value)
            result[key].update(saved.get(key) or {})
        else:
            result[key] = saved.get(key, value)
    return result


def load(nvm):
    try:
        if bytes(nvm[0:3]) == MAGIC:
            length = nvm[3] << 8 | nvm[4]
            return _merged(json.loads(bytes(nvm[5:5 + length])))
    except Exception as e:
        print("[STORE] could not read settings: %s" % e)
    return _merged({})


def save_later():
    global _due
    _due = time.monotonic() + SAVE_DELAY


def save_if_due(nvm, settings):
    global _due
    if _due is None or time.monotonic() < _due:
        return
    _due = None
    data = json.dumps(settings).encode()
    if 5 + len(data) > len(nvm):
        print("[STORE] settings too large")
        return
    nvm[0:5 + len(data)] = MAGIC + bytes((len(data) >> 8, len(data) & 255)) + data
    print("[STORE] saved %d bytes" % len(data))
