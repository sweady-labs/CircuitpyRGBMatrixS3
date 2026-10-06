# CircuitPy RGB Matrix (MatrixPortal S3)

Running the LED matrix web controller on an Adafruit MatrixPortal S3.

## What this is
A non-blocking CircuitPython app that runs animations on a 64×32 HUB75 RGB matrix and exposes a simple web UI / JSON API so you can change animations in real time without blocking the HTTP server.

## Hardware
- Adafruit MatrixPortal S3  
- 64×32 HUB75 RGB LED matrix (proper 5V power supply)  
- HUB75 ribbon/cable to the MatrixPortal S3 connector

## Software
- CircuitPython (8.x / 9.x recommended)  
- Copy needed libraries into `/lib` (from Adafruit bundle):
  - `adafruit_httpserver`
  - `adafruit_display_text`
  - `adafruit_bitmap_font`
  - `adafruit_requests` and `adafruit_connection_manager` (for the hub status)
  - other dependencies used by animations
- The files in `lib/` come from the 10.x bundle (`adafruit-circuitpython-bundle-10.x-mpy`). For another
  CircuitPython version, take them from the matching bundle.

## Quick setup
1. Flash CircuitPython to the MatrixPortal S3.  
2. Copy project files to CIRCUITPY:
   - `code.py`, `boot.py`, `settings.toml`, `web/`, `led_sequences/`, `lib/`  
3. Edit `settings.toml`:
   ```
   CIRCUITPY_WIFI_SSID = "your_ssid"
   CIRCUITPY_WIFI_PASSWORD = "your_password"
   HUB_URL = "http://<hub-ip>:5000/api/zusammenfassung"
   HUB_API_TOKEN = ""
   ```
   `HUB_URL` and `HUB_API_TOKEN` are only needed for the hub status (see below). Keep your real values on
   the device; the `settings.toml` in this repo only holds placeholders.
4. Connect the HUB75 display and power the matrix with a suitable 5V supply.  
5. Power the board; it will connect to WiFi and start the web server (IP printed to serial).

## Web UI & API
- UI: `http://<device-ip>/` (serves `/web/index.html`)  
- JSON endpoints:
  - `GET /api/animations` — list available animations
  - `GET /api/current` — current selection + play state
  - `POST /api/set` { "name": "<anim>" } — select animation
  - `POST /api/load-animation` — queue/start selected animation
  - `POST /api/stop-animation` — stop current animation
  - `GET /api/status` — elapsed/remaining time

## Where to find and edit the web interface
- Source file in the repo: `web/index.html`  
- On the device: copy the entire `web/` folder to the CIRCUITPY root so the board can serve it (path on device: `/web/index.html`).  
- Access from a browser on the same network at: `http://<device-ip>/` (default HTTP port 80).  
- How to discover the device IP:
  - Check the USB serial console after boot — the script prints the IP address when Wi‑Fi connects.
  - Or find the device in your router's DHCP client list.
- To customize the UI:
  1. Edit `web/index.html` locally.
  2. Copy the edited file(s) to the device's `/web/` folder.
  3. The web server serves files immediately; reload the browser to see changes.
- Static assets: If you add images, JS or CSS, place them in `/web/` alongside `index.html`.

## Animations
- Animations live in `led_sequences/`  
- Each non-blocking animation should implement:
  - `init_animation()` → initial state dict
  - `update_animation(state)` → draw one frame and return state
- Add new filenames (without `.py`) to `ANIMATIONS` in `code.py` (and `boot.py` if used).

## Hub status
The animation `hub_status` turns the matrix into a status display for the home hub
([sweady-labs/home-hub](https://github.com/sweady-labs/home-hub)). Every 60 seconds it reads
`GET /api/zusammenfassung` and shows three lines:

| Line | Shows | Colors |
| --- | --- | --- |
| 1 | Internet: `212 Mbit`, `Online`, `Offline` | green, red if offline, grey if unknown |
| 2 | Backup: `Backup ok`, `Backup ...` (running), `Backup alt` (stale), `Backup !!` (failed or stuck) | green, blue, yellow, red |
| 3 | `Alles ok` or the number of hints, e.g. `2 Hinweise` | green, yellow, red if at least one is a problem |

If the hub does not answer, line 1 says `Hub weg` and line 2 the reason (`keine Antw`, `HTTP 401` for a missing
or wrong token, `HTTP 403` if the matrix is outside `HUB_API_NETWORKS`, `HUB_URL ?` if the setting is missing).
The serial console prints the details.

Settings in `settings.toml` on the device:
- `HUB_URL` — full address of the summary endpoint, e.g. `http://<hub-ip>:5000/api/zusammenfassung`
- `HUB_API_TOKEN` — only if the hub has `HUB_API_TOKEN` set; sent as `Authorization: Bearer …`

To use it, select `hub_status` in the web UI and press Play. Unlike the other animations it has no 5 hour limit,
and if it was the selected animation it starts again by itself after a restart or power cut.

The decision what to show lives in `led_sequences/hub_lines.py`, plain Python without CircuitPython
modules. Its tests run on a computer:
```
python3 -m unittest tests/test_hub_lines.py
```

## Troubleshooting
- No image: check 5V power and HUB75 wiring (common ground).  
- WiFi fail: confirm `settings.toml` credentials.  
- Hub status says `Hub weg`: check `HUB_URL` and, if the hub uses one, `HUB_API_TOKEN`.  
- Errors: open serial console to view runtime prints.

License: MIT