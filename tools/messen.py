"""Shows every scene on the board for a few seconds and reports frames per second, time per frame
and errors, as measured by the board itself (/api/state).

    python3 tools/messen.py                    # all scenes, board at ledmatrix.local
    python3 tools/messen.py feuer plasma --host 192.168.178.49 --sekunden 8

Afterwards the scene that was running before is shown again. Only the standard library is needed.
"""
import argparse
import json
import time
import urllib.request


def call(host, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request("http://%s%s" % (host, path), data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("scenes", nargs="*")
    parser.add_argument("--host", default="ledmatrix.local")
    parser.add_argument("--sekunden", type=float, default=6)
    args = parser.parse_args()

    before = call(args.host, "/api/state")["scene"]
    ids = args.scenes or [s["id"] for s in call(args.host, "/api/scenes")]
    print("%-18s %6s %9s %6s  %s" % ("scene", "fps", "frame ms", "target", "error"))
    try:
        for scene_id in ids:
            call(args.host, "/api/scene", {"id": scene_id})
            time.sleep(args.sekunden)
            state = call(args.host, "/api/state")
            print("%-18s %6.1f %9.1f %6d  %s" % (scene_id, state["fps"], state["frame_ms"], state["fps_target"],
                                                  state["error"] or ""))
    finally:
        call(args.host, "/api/scene", {"id": before})


if __name__ == "__main__":
    main()
