"""Runs one scene at a time: loads it, gives it frames at its own rate, switches scenes and
applies brightness, night mode and the playlist.

A scene is a module in scenes/ with

    FPS = 30                      # optional, frames per second
    class Scene:
        def __init__(self, group, settings): ...   # build layers in group
        def frame(self, dt): ...                   # dt = seconds since the last frame

Everything a scene draws goes into its group. When the scene ends, the group is removed and the
module is unloaded again, so memory stays free for the next one.
"""
import gc
import sys
import time

import displayio

from app import clock, gfx, store
from scenes import SCENES

IDS = [scene[0] for scene in SCENES]


class Engine:
    def __init__(self, display, matrix, settings):
        self.display = display
        self.matrix = matrix
        self.settings = settings
        self.root = displayio.Group()
        display.root_group = self.root
        self.group = None
        self.scene = None
        self.scene_id = None
        self.module_name = None
        self.error = None
        self.frame_ns = 33_333_333
        self.next_ns = 0
        self.last_ns = 0
        self.level = None
        self.switched_at = time.monotonic()
        self.fps = 0.0
        self.frame_ms = 0.0  # average time of scene.frame() plus display refresh
        self._frames = 0
        self._busy_ns = 0
        self._fps_since = time.monotonic_ns()
        self.night_active = False

    # --- Scenes -----------------------------------------------------------------------

    def show(self, scene_id):
        """Switch to a scene now. Unknown ids fall back to the first scene."""
        if scene_id not in IDS:
            scene_id = IDS[0]
        self._unload()
        self.group = displayio.Group()
        self.root.append(self.group)
        self.scene_id = scene_id
        self.module_name = "scenes." + scene_id
        self.switched_at = time.monotonic()
        self.error = None
        try:
            module = __import__(self.module_name, None, None, ["Scene"])
            self.frame_ns = 1_000_000_000 // getattr(module, "FPS", 30)
            self.scene = module.Scene(self.group, self.settings)
        except Exception as e:
            self._failed(e)
        self.next_ns = 0
        self.last_ns = time.monotonic_ns()
        if self.settings["scene"] != scene_id:
            self.settings["scene"] = scene_id
            store.save_later()
        gc.collect()
        print("[SCENE] %s (%d KB free)" % (scene_id, gc.mem_free() // 1024))

    def step(self, delta):
        """Next (+1) or previous (-1) scene in the order of the registry."""
        self.show(IDS[(IDS.index(self.scene_id) + delta) % len(IDS)])

    def restart(self):
        self.show(self.scene_id)

    def _unload(self):
        self.scene = None
        if self.group is not None:
            self.root.remove(self.group)
            self.group = None
        gfx.forget_palettes()
        if self.module_name in sys.modules:
            del sys.modules[self.module_name]
        gc.collect()

    def _failed(self, e):
        print("[SCENE] %s failed:" % self.scene_id)
        try:
            import traceback
            traceback.print_exception(e)
        except Exception:
            print(e)
        self.error = "%s: %s" % (type(e).__name__, e)
        self.scene = None
        while len(self.group):
            self.group.pop()
        gfx.forget_palettes()
        gfx.Label(self.group, "Fehler", 0xFF3030, y=3, center=True)
        gfx.Label(self.group, self.scene_id[:12], 0x808080, y=14, center=True)
        self.display.refresh()

    # --- Frames -----------------------------------------------------------------------

    def tick(self):
        """Draw the next frame if it is due. Call as often as possible."""
        if self.scene is None or not self.level:
            return
        now = time.monotonic_ns()
        if now < self.next_ns:
            return
        dt = min((now - self.last_ns) / 1e9, 0.25)
        self.last_ns = now
        # catch up at most one frame, otherwise start the rhythm again from now
        self.next_ns = max(self.next_ns + self.frame_ns, now)
        try:
            self.scene.frame(dt)
        except Exception as e:
            self._failed(e)
            return
        self.display.refresh()
        self._frames += 1
        self._busy_ns += time.monotonic_ns() - now
        if now - self._fps_since >= 2_000_000_000:
            self.fps = self._frames * 1e9 / (now - self._fps_since)
            self.frame_ms = self._busy_ns / self._frames / 1e6
            self._frames = 0
            self._busy_ns = 0
            self._fps_since = now

    # --- Brightness, night mode, playlist (call about once a second) ------------------

    def update(self):
        s = self.settings
        local = clock.now()
        night = s["night"]
        self.night_active = bool(
            night["on"] and local is not None and clock.in_window(local.tm_hour * 60 + local.tm_min, night["start"], night["end"])
        )
        if not s["on"]:
            level = 0
        elif self.night_active:
            level = night["level"] / 100
        else:
            level = s["brightness"] / 100
        self.set_level(level)

        playlist = s["playlist"]
        scenes = [scene_id for scene_id in playlist["scenes"] if scene_id in IDS]
        if playlist["on"] and scenes and time.monotonic() - self.switched_at >= playlist["minutes"] * 60:
            index = scenes.index(self.scene_id) + 1 if self.scene_id in scenes else 0
            self.show(scenes[index % len(scenes)])

    def set_level(self, level):
        if level == self.level:
            return
        was_off = not self.level
        self.level = level
        if level:
            gfx.set_brightness(level)
            self.matrix.brightness = 1.0
            if was_off:
                self.next_ns = 0
                self.last_ns = time.monotonic_ns()
        else:
            self.matrix.brightness = 0.0
        print("[LEVEL] %d %%" % round(level * 100))

    # --- For the web interface ---------------------------------------------------------

    def state(self):
        s = self.settings
        local = clock.now()
        return {
            "scene": self.scene_id,
            "error": self.error,
            "on": s["on"],
            "brightness": s["brightness"],
            "level": round((self.level or 0) * 100),
            "night_active": self.night_active,
            "playlist": s["playlist"],
            "night": s["night"],
            "message": s["message"],
            "time": "%02d:%02d" % (local.tm_hour, local.tm_min) if local else None,
            "fps": round(self.fps, 1),
            "fps_target": round(1e9 / self.frame_ns),
            "frame_ms": round(self.frame_ms, 1),
            "free_kb": gc.mem_free() // 1024,
            "uptime_s": int(time.monotonic()),
        }
