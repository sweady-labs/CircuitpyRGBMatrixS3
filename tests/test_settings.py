"""Settings in the NVM (app/store.py) and checking what the web interface sends (app/web.py).

    python3 -m unittest tests/test_settings.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "sim"))  # stand-ins for adafruit_httpserver and displayio

from app import store, web  # noqa: E402


class StoreTests(unittest.TestCase):
    def test_empty_nvm_gives_defaults(self):
        self.assertEqual(store.load(bytearray(8192)), store._merged({}))

    def test_old_bytes_of_the_first_version_give_defaults(self):
        nvm = bytearray(8192)
        nvm[0], nvm[1] = 24, 1  # animation index and mode of the first version
        self.assertEqual(store.load(nvm)["scene"], store.DEFAULTS["scene"])

    def test_saved_settings_come_back(self):
        nvm = bytearray(8192)
        settings = store.load(nvm)
        settings["scene"] = "feuer"
        settings["night"]["level"] = 10
        store.save_later()
        store._due = 0  # due now
        store.save_if_due(nvm, settings)
        self.assertEqual(store.load(nvm), settings)

    def test_new_default_keys_survive_old_saves(self):
        loaded = store._merged({"scene": "plasma", "night": {"on": True}})
        self.assertEqual(loaded["scene"], "plasma")
        self.assertTrue(loaded["night"]["on"])
        self.assertEqual(loaded["night"]["start"], store.DEFAULTS["night"]["start"])
        self.assertIn("playlist", loaded)


class WebInputTests(unittest.TestCase):
    def setUp(self):
        self.settings = store._merged({})

    def test_valid_settings_are_taken(self):
        rejected = web.apply_settings(self.settings, {
            "on": False, "brightness": 35,
            "playlist": {"on": True, "minutes": 15, "scenes": ["uhr", "plasma"]},
            "night": {"on": True, "start": "23:00", "end": "07:15", "level": 5},
        })
        self.assertEqual(rejected, [])
        self.assertFalse(self.settings["on"])
        self.assertEqual(self.settings["brightness"], 35)
        self.assertEqual(self.settings["playlist"], {"on": True, "minutes": 15, "scenes": ["uhr", "plasma"]})
        self.assertEqual(self.settings["night"], {"on": True, "start": "23:00", "end": "07:15", "level": 5})

    def test_invalid_values_are_rejected_and_nothing_changes(self):
        before = store._merged({})
        rejected = web.apply_settings(self.settings, {
            "brightness": 0, "playlist": {"minutes": 7}, "night": {"start": "25:00", "end": "7:5", "level": 300},
        })
        self.assertEqual(sorted(rejected), ["brightness", "night.end", "night.level", "night.start", "playlist.minutes"])
        self.assertEqual(self.settings, before)

    def test_unknown_scenes_are_dropped_from_the_playlist(self):
        web.apply_settings(self.settings, {"playlist": {"scenes": ["uhr", "gibtsnicht"]}})
        self.assertEqual(self.settings["playlist"]["scenes"], ["uhr"])

    def test_message(self):
        rejected = web.apply_message(self.settings, {"text": "  Essen ist fertig!  ", "color": "#3DDC84", "speed": 5})
        self.assertEqual(rejected, [])
        self.assertEqual(self.settings["message"], {"text": "Essen ist fertig!", "color": "#3DDC84", "speed": 5})

    def test_message_checks(self):
        self.assertEqual(web.apply_message(self.settings, {"text": " "}), ["text"])
        self.assertEqual(web.apply_message(self.settings, {"text": "x", "color": "rot", "speed": 9}), ["color", "speed"])
        web.apply_message(self.settings, {"text": "a" * 500, "color": "bunt"})
        self.assertEqual(len(self.settings["message"]["text"]), 200)
        self.assertEqual(self.settings["message"]["color"], "bunt")


if __name__ == "__main__":
    unittest.main()
