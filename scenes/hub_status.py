"""Hub-Status: internet, backup and hints of the home hub (/api/zusammenfassung), one line each.

Asks the hub every POLL_SECONDS. Address and optional token come from settings.toml (HUB_URL,
HUB_API_TOKEN). Red lines pulse slowly, so a problem catches the eye in passing.
"""
import math
import os

from app import gfx
from app.hub_lines import GREY, RED, status_lines

FPS = 15
PREVIEW_AT = 1.0
POLL_SECONDS = 60
REQUEST_TIMEOUT = 4
ROWS = (1, 12, 23)


class Scene:
    def __init__(self, group, settings):
        self.url = os.getenv("HUB_URL") or ""
        self.token = os.getenv("HUB_API_TOKEN") or ""
        self.session = None
        self.bitmap, self.pal = gfx.canvas(group, [0, 0, 0, 0])
        self.lines = [("Hub ...", GREY), ("", GREY), ("", GREY)]
        self.icons = ("net", "backup", "bell")
        self.draw()
        self.wait = 0.0  # first request in the first frame, after the placeholder is visible
        self.phase = 0.0

    def fetch(self):
        if not self.url:
            return "HUB_URL ?"
        try:
            if self.session is None:
                import adafruit_connection_manager
                import adafruit_requests
                import wifi

                pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
                self.session = adafruit_requests.Session(pool)
            headers = {"Authorization": "Bearer " + self.token} if self.token else {}
            with self.session.get(self.url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status_code != 200:
                    print("[HUB] HTTP %d" % response.status_code)
                    return "HTTP %d" % response.status_code
                return response.json()
        except Exception as e:
            print("[HUB] request failed: %s" % e)
            return "keine Antw"

    def draw(self):
        self.bitmap.fill(0)
        for row, ((text, color), y) in enumerate(zip(self.lines, ROWS)):
            index = row + 1
            self.pal[index] = color
            if text:
                gfx.draw_icon(self.bitmap, self.icons[row], 1, y, index)
                gfx.draw_text(self.bitmap, text, 11, y, index)

    def frame(self, dt):
        self.wait -= dt
        if self.wait <= 0:
            self.wait = POLL_SECONDS
            result = self.fetch()
            self.lines = status_lines(result)
            if isinstance(result, dict):
                status = result.get("status")
                self.icons = ("net", "backup", "ok" if status == "ok" else "warn" if status == "problem" else "bell")
            else:
                self.icons = ("warn", "net", "net")
            self.draw()

        # red lines pulse slowly, everything else stays calm
        self.phase += dt
        pulse = 0.55 + 0.45 * math.cos(self.phase * 2.4)
        for row, (text, color) in enumerate(self.lines):
            if color == RED:
                self.pal[row + 1] = gfx.scale(RED, pulse)
