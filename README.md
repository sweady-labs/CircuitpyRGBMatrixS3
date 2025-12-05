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
  - other dependencies used by animations

## Quick setup
1. Flash CircuitPython to the MatrixPortal S3.  
2. Copy project files to CIRCUITPY:
   - `code.py`, `boot.py`, `settings.toml`, `web/`, `led_sequences/`, `lib/`  
3. Edit `settings.toml`:
   ```
   CIRCUITPY_WIFI_SSID = "your_ssid"
   CIRCUITPY_WIFI_PASSWORD = "your_password"
   ```
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

## Troubleshooting
- No image: check 5V power and HUB75 wiring (common ground).  
- WiFi fail: confirm `settings.toml` credentials.  
- Errors: open serial console to view runtime prints.

License: MIT