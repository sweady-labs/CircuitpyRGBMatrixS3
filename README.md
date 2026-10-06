# LED matrix in the hallway (MatrixPortal S3)

CircuitPython firmware for an Adafruit MatrixPortal S3 with a 64×32 HUB75 RGB matrix. It plays scenes –
a clock, a scrolling message, the status of the home hub, ambient and effect scenes, self-playing games,
Christmas scenes – and is controlled from a web interface in the home network.

- **Web interface:** <http://ledmatrix.local/> (or the IP of the board, currently `192.168.178.49`):
  live picture of the matrix, scenes with previews, brightness, on/off, scrolling message,
  automatic scene change and night mode. Works on a phone.
- **Buttons on the board:** UP shows the next scene, DOWN switches the matrix on or off.
- After a restart or power cut the last scene comes back by itself; all settings survive.

## Hardware and setup

- Adafruit MatrixPortal S3, 64×32 HUB75 matrix, 5 V power supply for the matrix
- CircuitPython 10.x on the board

1. Copy the firmware to the board (it appears as `CIRCUITPY`):
   ```bash
   tools/deploy.sh
   ```
   This copies `code.py`, `app/`, `scenes/`, `web/` and the libraries from `lib/`, and removes the files
   of the first version. `settings.toml` on the board is never touched.
2. Create `settings.toml` on the board (the one in the repo only has placeholders):
   ```toml
   CIRCUITPY_WIFI_SSID = "..."
   CIRCUITPY_WIFI_PASSWORD = "..."
   HUB_URL = "http://192.168.178.111:5000/api/zusammenfassung"   # for the scene Hub-Status
   HUB_API_TOKEN = ""                                             # only if the hub wants one
   ```
3. The board restarts by itself after copying. The serial console shows the address.

## API

Everything the web interface does goes through a small JSON API, so it also works from Siri shortcuts,
n8n or `curl`. No login – it is only reachable in the home network.

| Request | What it does |
| --- | --- |
| `GET /api/state` | current scene, brightness, playlist, night mode, message, time, frames per second |
| `GET /api/scenes` | all scenes with `id`, `title`, `group` |
| `GET /api/frame` | the picture on the matrix right now: 64×32 pixels RGB565, little endian (4096 bytes) |
| `POST /api/scene` | `{"id": "uhr"}` or `{"step": 1}` / `{"step": -1}` |
| `POST /api/settings` | any of `on`, `brightness` (1-100), `playlist` `{on, minutes, scenes}`, `night` `{on, start, end, level}` |
| `POST /api/message` | `{"text": "Essen ist fertig!", "color": "#3DDC84" or "bunt", "speed": 1-5}` – shows it at once |

```bash
curl -X POST -H 'Content-Type: application/json' -d '{"text": "Essen ist fertig!"}' http://ledmatrix.local/api/message
```

Invalid values are answered with status 400 and the list of `rejected` fields; valid parts are still taken.

## How it is built

```
code.py            starts the matrix, the last scene, WiFi and the web server; main loop
app/engine.py      runs one scene at a time, frame timing, brightness, night mode, playlist
app/gfx.py         palettes with gamma and brightness, colors, text and pixel art helpers
app/font.py        pixel fonts (normal with umlauts, big clock digits, icons)
app/store.py       settings as JSON in the NVM of the microcontroller
app/clock.py       NTP and German summer/winter time
app/web.py         HTTP API
app/hub_lines.py   what the Hub-Status scene shows (plain Python, tested)
scenes/            one module per scene, registered in scenes/__init__.py
web/               index.html (the web interface) and vorschau.png (previews of all scenes)
tools/sim/         stand-ins for displayio, bitmaptools, vectorio and ulab to run scenes on a computer
tools/vorschau.py  renders scenes as PNG/GIF and builds web/vorschau.png
tools/deploy.sh    copies the firmware to the board
```

The matrix is set up once in `code.py`; a scene only draws into its own `displayio.Group`. Colors in scenes are
written as they should look; `app/gfx.py` applies gamma correction and the current brightness to every palette,
so brightness and night mode work for all scenes without them knowing. Full screen effects are computed with
`ulab` (numpy for microcontrollers, built into CircuitPython), everything else with sprites, shapes and palette
animation. **How to write a scene, and what each operation costs on the board: [scenes/README.md](scenes/README.md).**

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install numpy pillow   # only for simulator and previews
.venv/bin/python tools/vorschau.py plasma                      # vorschau/plasma.gif and .png
.venv/bin/python tools/vorschau.py --alle --sprite             # all scenes, contact sheet, web/vorschau.png
.venv/bin/python -m unittest discover tests                    # tests (scene tests need numpy)
tools/deploy.sh                                                # to the board
```

After adding or changing scenes, run `tools/vorschau.py --alle --sprite` so the web interface shows current previews.
`/api/state` reports `fps` and `frame_ms` (time per frame) of the running scene – handy to check a new scene on the board.

## Troubleshooting

- **No picture:** check the 5 V supply of the matrix and the HUB75 cable.
- **Not in the WiFi:** check SSID and password in `settings.toml` on the board; the serial console shows `[WEB] no network: ...`.
  Without WiFi the matrix keeps playing and retries every 30 seconds.
- **Clock shows `--:--`:** no answer from `pool.ntp.org` yet; it retries every minute.
- **Hub-Status says `Hub weg`:** check `HUB_URL` and, if the hub uses one, `HUB_API_TOKEN`
  (`HTTP 401` = token, `HTTP 403` = the matrix is outside `HUB_API_NETWORKS` of the hub).
- **A scene shows "Fehler":** the serial console has the traceback; `/api/state` has it in `error`.

License: MIT
