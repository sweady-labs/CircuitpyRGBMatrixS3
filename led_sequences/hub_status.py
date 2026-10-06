"""
hub_status.py - Status of the home hub on the matrix

Asks the hub for /api/zusammenfassung every POLL_SECONDS and shows three lines:
internet, backup and the number of hints. Address and optional token come from
settings.toml (HUB_URL, HUB_API_TOKEN).
"""
import os
import time
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import wifi
import adafruit_connection_manager
import adafruit_requests
from adafruit_display_text import label

from led_sequences.hub_lines import status_lines

NO_TIMEOUT = True  # code.py: keep running, no 5 hour limit for a status display
POLL_SECONDS = 60
REQUEST_TIMEOUT = 5

HUB_URL = os.getenv("HUB_URL") or ""
HUB_API_TOKEN = os.getenv("HUB_API_TOKEN") or ""

displayio.release_displays()

WIDTH = 64
HEIGHT = 32

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH, height=HEIGHT, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

group = displayio.Group()
lines = []
for y in (4, 15, 26):
    line = label.Label(terminalio.FONT, text="", color=0, x=1, y=y)
    lines.append(line)
    group.append(line)
display.root_group = group

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
requests = adafruit_requests.Session(pool)


def fetch():
    """Summary as dict, or a short error text for the display."""
    if not HUB_URL:
        return "HUB_URL ?"
    headers = {"Authorization": "Bearer " + HUB_API_TOKEN} if HUB_API_TOKEN else {}
    try:
        with requests.get(HUB_URL, headers=headers, timeout=REQUEST_TIMEOUT) as response:
            if response.status_code != 200:
                print("[HUB] HTTP %d" % response.status_code)
                return "HTTP %d" % response.status_code
            return response.json()
    except Exception as e:
        print("[HUB] Request failed: %s" % str(e))
        return "keine Antw"


def show(result):
    for line, (text, color) in zip(lines, status_lines(result)):
        line.text = text
        line.color = color


def init_animation():
    """Initialize animation state"""
    show(fetch())
    return {"next_poll": time.monotonic() + POLL_SECONDS}


def update_animation(state):
    """Ask the hub again once POLL_SECONDS have passed"""
    if time.monotonic() >= state["next_poll"]:
        show(fetch())
        state["next_poll"] = time.monotonic() + POLL_SECONDS
    return state
