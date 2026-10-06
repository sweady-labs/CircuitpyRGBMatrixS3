"""LED matrix: scenes on a 64x32 HUB75 matrix, controlled from a web interface in the home network.

Starts the last scene right away, then connects to WiFi and serves the web interface and the API.
The main loop draws frames, answers HTTP requests, reads the two buttons and once a second checks
brightness, night mode, playlist, clock and whether settings need saving.
"""
import os
import time

import board
import displayio
import framebufferio
import keypad
import microcontroller
import rgbmatrix
import supervisor
import wifi

from app import clock, store
from app.engine import Engine

HOSTNAME = "ledmatrix"  # http://ledmatrix.local/
BIT_DEPTH = 5
# A short restart every night at 04:00: after hours of running and many scene changes the memory
# gets scattered and the heavy scenes slow down (see scenes/README.md). Takes about two seconds.
NIGHTLY_RELOAD = (4, 0)

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=BIT_DEPTH,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1, board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

settings = store.load(microcontroller.nvm)
engine = Engine(display, matrix, settings)
engine.update()
engine.show(settings["scene"])

# UP: next scene, DOWN: matrix on/off
buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)


def start_network():
    """Connects to WiFi and starts the web server. Returns (pool, server) or (None, None)."""
    import mdns
    import socketpool
    from adafruit_httpserver import Server

    from app import web

    try:
        if not wifi.radio.connected:
            wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        pool = socketpool.SocketPool(wifi.radio)
        server = Server(pool, "/web", debug=False)
        web.add_routes(server, engine, matrix)
        server.start(str(wifi.radio.ipv4_address), 80)
        try:
            responder = mdns.Server(wifi.radio)
            responder.hostname = HOSTNAME
            responder.advertise_service(service_type="_http", protocol="_tcp", port=80)
        except Exception as e:
            print("[MDNS] %s" % e)
        print("[WEB] http://%s/  http://%s.local/" % (wifi.radio.ipv4_address, HOSTNAME))
        return pool, server
    except Exception as e:
        print("[WEB] no network: %s" % e)
        return None, None


pool, server = start_network()
started = time.monotonic()
next_second = started
retry_network = next_second + 30

while True:
    engine.tick()

    if server is not None:
        try:
            server.poll()
        except Exception as e:
            print("[WEB] %s" % e)

    event = buttons.events.get()
    if event and event.pressed:
        if event.key_number == 0:
            engine.step(1)
        else:
            settings["on"] = not settings["on"]
            store.save_later()
            engine.update()

    if time.monotonic() >= next_second:
        next_second = time.monotonic() + 1
        engine.update()
        store.save_if_due(microcontroller.nvm, settings)
        local = clock.now()
        if local and (local.tm_hour, local.tm_min) == NIGHTLY_RELOAD and time.monotonic() - started > 3600:
            store.save_now(microcontroller.nvm, settings)
            supervisor.reload()
        if server is None:
            if next_second >= retry_network:
                retry_network = next_second + 30
                pool, server = start_network()
        elif not wifi.radio.connected:
            print("[WEB] WiFi lost")
            server.stop()
            pool, server = None, None
            retry_network = next_second + 5
        else:
            clock.sync_if_due(pool)

    # a short rest: frees the CPU between frames and lets Ctrl-C on the serial console stop the program
    time.sleep(0.001)
