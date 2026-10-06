"""Every scene runs a few seconds in the simulator (tools/sim) without an error.

Needs numpy and Pillow (see tools/vorschau.py); without them the tests are skipped:
    .venv/bin/python -m unittest tests/test_scenes.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401
except ImportError:
    numpy = None


@unittest.skipIf(numpy is None, "numpy and Pillow are needed for the simulator")
class SceneTests(unittest.TestCase):
    def test_every_scene_runs(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import vorschau

        from scenes import SCENES

        for scene_id, title, group in SCENES:
            with self.subTest(scene=scene_id):
                frames, fps, preview_at = vorschau.run(scene_id, 4, 1.0)
                self.assertTrue(frames)
                # something is lit at the preview moment (no scene is a black screen)
                self.assertGreater(vorschau.still(frames, fps, preview_at).max(), 0)


if __name__ == "__main__":
    unittest.main()
