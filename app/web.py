"""HTTP API for the web interface (and for anything else in the home network, e.g. Siri or n8n).

GET  /api/state      current scene, brightness, playlist, night mode, message, time, fps
GET  /api/scenes     all scenes: id, title, group
GET  /api/frame      the picture on the matrix right now, 64x32 pixels RGB565 (4096 bytes)
POST /api/scene      {"id": "plasma"} or {"step": 1} / {"step": -1}
POST /api/settings   any of {"on", "brightness", "playlist", "night"}, partial updates
POST /api/message    {"text": "...", "color": "#FFB000" or "bunt", "speed": 1-5}, shows it at once

Static files (index.html, preview sprite) come from /web.
"""
from adafruit_httpserver import BAD_REQUEST_400, GET, OK_200, POST, JSONResponse, Request, Response

from app import store
from scenes import SCENES

IDS = [scene[0] for scene in SCENES]

MINUTES = (1, 2, 5, 10, 15, 30, 60, 120)


def _time_ok(text):
    try:
        hours, mins = text.split(":")
        return len(hours) == 2 and len(mins) == 2 and 0 <= int(hours) < 24 and 0 <= int(mins) < 60
    except Exception:
        return False


def _color_ok(text):
    if text == "bunt":
        return True
    try:
        return len(text) == 7 and text[0] == "#" and int(text[1:], 16) >= 0
    except Exception:
        return False


def apply_settings(settings, data):
    """Takes over the valid parts of data; returns the list of rejected keys."""
    rejected = []
    if "on" in data:
        settings["on"] = bool(data["on"])
    if "brightness" in data:
        value = data["brightness"]
        if isinstance(value, int) and 1 <= value <= 100:
            settings["brightness"] = value
        else:
            rejected.append("brightness")
    playlist = data.get("playlist")
    if isinstance(playlist, dict):
        target = settings["playlist"]
        if "on" in playlist:
            target["on"] = bool(playlist["on"])
        if playlist.get("minutes") in MINUTES:
            target["minutes"] = playlist["minutes"]
        elif "minutes" in playlist:
            rejected.append("playlist.minutes")
        if isinstance(playlist.get("scenes"), list):
            target["scenes"] = [scene_id for scene_id in playlist["scenes"] if scene_id in IDS]
    night = data.get("night")
    if isinstance(night, dict):
        target = settings["night"]
        if "on" in night:
            target["on"] = bool(night["on"])
        for key in ("start", "end"):
            if key in night:
                if _time_ok(night[key]):
                    target[key] = night[key]
                else:
                    rejected.append("night." + key)
        if "level" in night:
            if isinstance(night["level"], int) and 0 <= night["level"] <= 100:
                target["level"] = night["level"]
            else:
                rejected.append("night.level")
    return rejected


def apply_message(settings, data):
    rejected = []
    message = settings["message"]
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        message["text"] = text.strip()[:200]
    else:
        rejected.append("text")
    if "color" in data:
        if _color_ok(data["color"]):
            message["color"] = data["color"]
        else:
            rejected.append("color")
    if "speed" in data:
        if isinstance(data["speed"], int) and 1 <= data["speed"] <= 5:
            message["speed"] = data["speed"]
        else:
            rejected.append("speed")
    return rejected


def add_routes(server, engine, matrix):
    def answer(request, rejected=()):
        state = engine.state()
        if rejected:
            state["rejected"] = list(rejected)
        return JSONResponse(request, state, status=BAD_REQUEST_400 if rejected else OK_200)

    @server.route("/api/state", GET)
    def state(request: Request):
        return answer(request)

    @server.route("/api/scenes", GET)
    def scenes(request: Request):
        return JSONResponse(request, [{"id": s[0], "title": s[1], "group": s[2]} for s in SCENES])

    @server.route("/api/frame", GET)
    def frame(request: Request):
        return Response(request, bytes(memoryview(matrix)), content_type="application/octet-stream")

    @server.route("/api/scene", POST)
    def scene(request: Request):
        data = request.json() or {}
        if data.get("id") in IDS:
            engine.show(data["id"])
        elif data.get("step") in (1, -1):
            engine.step(data["step"])
        else:
            return answer(request, ["id"])
        return answer(request)

    @server.route("/api/settings", POST)
    def settings(request: Request):
        rejected = apply_settings(engine.settings, request.json() or {})
        store.save_later()
        engine.update()
        return answer(request, rejected)

    @server.route("/api/message", POST)
    def message(request: Request):
        rejected = apply_message(engine.settings, request.json() or {})
        if "text" not in rejected:
            store.save_later()
            engine.show("laufschrift")
        return answer(request, rejected)
