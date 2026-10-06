"""Hub-Status: internet, backup and hints of the home hub (/api/zusammenfassung), one line each.

Asks the hub every POLL_SECONDS. Address and optional token come from settings.toml (HUB_URL,
HUB_API_TOKEN). Red lines pulse slowly, so a problem catches the eye in passing.

The request is plain HTTP over a socket instead of adafruit_requests: the hub speaks plain HTTP, and
adafruit_requests with its connection manager left the whole board measurably slower afterwards.
"""
import json
import math
import os

from app import gfx
from app.hub_lines import GREY, RED, status_lines

FPS = 15
PREVIEW_AT = 1.0
POLL_SECONDS = 60
REQUEST_TIMEOUT = 4
ROWS = (1, 12, 23)


def http_get(url, token):
    """GET over plain HTTP/1.0, so the hub answers with the whole body and closes. Returns (status, body)."""
    import socketpool
    import wifi

    host_port, _, path = url[len("http://"):].partition("/")
    host, _, port = host_port.partition(":")
    pool = socketpool.SocketPool(wifi.radio)
    address = pool.getaddrinfo(host, int(port or 80))[0][4]
    sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    sock.settimeout(REQUEST_TIMEOUT)
    try:
        sock.connect(address)
        request = "GET /%s HTTP/1.0\r\nHost: %s\r\n" % (path, host)
        if token:
            request += "Authorization: Bearer %s\r\n" % token
        sock.send((request + "\r\n").encode())
        data = bytearray()
        chunk = bytearray(1024)
        while True:
            count = sock.recv_into(chunk)
            if not count:
                break
            data.extend(chunk[:count])
    finally:
        sock.close()
    head, _, body = bytes(data).partition(b"\r\n\r\n")
    return int(head.split(b" ")[1]), body


class Scene:
    def __init__(self, group, settings):
        self.url = os.getenv("HUB_URL") or ""
        self.token = os.getenv("HUB_API_TOKEN") or ""
        self.bitmap, self.pal = gfx.canvas(group, [0, 0, 0, 0])
        self.lines = [("Hub ...", GREY), ("", GREY), ("", GREY)]
        self.icons = ("net", "backup", "bell")
        self.draw()
        self.wait = 0.0  # first request in the first frame, after the placeholder is visible
        self.phase = 0.0

    def fetch(self):
        """The hub's summary as dict, or a short error text for the display."""
        if not self.url.startswith("http://"):
            return "HUB_URL ?"
        try:
            status, body = http_get(self.url, self.token)
        except Exception as e:
            print("[HUB] request failed: %s" % e)
            return "keine Antw"
        if status != 200:
            print("[HUB] HTTP %d" % status)
            return "HTTP %d" % status
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            return "kein JSON"

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
