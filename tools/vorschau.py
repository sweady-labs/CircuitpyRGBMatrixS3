"""Runs scenes on the computer in the simulator (tools/sim) and saves what the matrix would show.

    python tools/vorschau.py plasma feuer          # vorschau/plasma.gif + .png, vorschau/feuer.gif + .png
    python tools/vorschau.py --alle                # every scene, plus vorschau/alle.png (contact sheet)
    python tools/vorschau.py --alle --sprite       # also web/vorschau.png, the pictures in the web interface

Options: --sekunden 6 (length of the GIF), --hell 30 (brightness in percent, e.g. for night mode).
Needs numpy and Pillow: python3 -m venv .venv && .venv/bin/pip install numpy pillow

The colors are simulated like the LEDs show them: RGB565, the bit depth of code.py and the
gamma of the LEDs. A scene can set PREVIEW_AT = seconds for the moment of its still picture.
"""
import argparse
import importlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "sim"))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import cp_modules  # noqa: E402

cp_modules.install()

import displayio  # noqa: E402
import framebufferio  # noqa: E402
import rgbmatrix  # noqa: E402
from app import gfx, store  # noqa: E402
from scenes import SCENES  # noqa: E402

OUT = os.path.join(ROOT, "vorschau")
with open(os.path.join(ROOT, "code.py")) as _f:
    BIT_DEPTH = int(re.search(r"^BIT_DEPTH = (\d+)", _f.read(), re.M).group(1))
LED = 8  # pixels per LED in the GIFs


def panel(picture):
    """RGB888 as sent to the matrix -> RGB888 as the LEDs look on a computer screen."""
    channels = []
    for channel, bits in ((picture[..., 0] >> 3, 5), (picture[..., 1] >> 2, 6), (picture[..., 2] >> 3, 5)):
        keep = min(bits, BIT_DEPTH)
        duty = (channel >> (bits - keep)) / ((1 << keep) - 1)
        channels.append(255 * duty ** (1 / 2.2))
    return np.stack(channels, axis=-1).astype(np.uint8)


def _led_mask():
    yy, xx = np.mgrid[0:LED, 0:LED] + 0.5
    dist = np.sqrt((xx - LED / 2) ** 2 + (yy - LED / 2) ** 2)
    return np.clip(LED * 0.42 - dist + 0.5, 0, 1)[..., None]


MASK = _led_mask()


def led_look(picture):
    big = np.repeat(np.repeat(picture.astype(float), LED, axis=0), LED, axis=1)
    tile = np.tile(MASK, (picture.shape[0], picture.shape[1], 1))
    background = np.array([10, 10, 12], dtype=float)
    return (big * tile + background * (1 - tile)).astype(np.uint8)


def run(scene_id, seconds, level):
    """All frames of a scene as panel pictures, and its frame rate."""
    gfx.forget_palettes()
    gfx.set_brightness(level)
    matrix = rgbmatrix.RGBMatrix(width=64, height=32, bit_depth=BIT_DEPTH)
    display = framebufferio.FramebufferDisplay(matrix)
    root = displayio.Group()
    display.root_group = root
    group = displayio.Group()
    root.append(group)
    module = importlib.import_module("scenes." + scene_id)
    fps = getattr(module, "FPS", 30)
    scene = module.Scene(group, store.load(bytearray(16)))
    frames = []
    for _ in range(int(seconds * fps)):
        scene.frame(1 / fps)
        display.refresh()
        frames.append(panel(display.picture))
    return frames, fps, getattr(module, "PREVIEW_AT", 3.0)


def still(frames, fps, at):
    return frames[min(len(frames) - 1, int(at * fps))]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("scenes", nargs="*")
    parser.add_argument("--alle", action="store_true")
    parser.add_argument("--sprite", action="store_true")
    parser.add_argument("--sekunden", type=float, default=6)
    parser.add_argument("--hell", type=int, default=100)
    args = parser.parse_args()

    ids = [s[0] for s in SCENES] if args.alle else args.scenes
    titles = {s[0]: s[1] for s in SCENES}
    os.makedirs(OUT, exist_ok=True)
    os.environ.setdefault("HUB_URL", "http://hub.sim/api/zusammenfassung")  # answered by tools/sim/adafruit_requests.py
    stills = {}
    for scene_id in ids:
        frames, fps, at = run(scene_id, max(args.sekunden, 0.5), args.hell / 100)
        picture = still(frames, fps, at) if at < args.sekunden else frames[-1]
        stills[scene_id] = picture
        Image.fromarray(led_look(picture)).save(os.path.join(OUT, scene_id + ".png"))
        step = max(1, round(fps / 20))
        gif = [Image.fromarray(led_look(f)) for f in frames[::step]]
        gif[0].save(os.path.join(OUT, scene_id + ".gif"), save_all=True, append_images=gif[1:],
                    duration=int(1000 * step / fps), loop=0)
        print("%-14s %3d frames at %d fps" % (scene_id, len(frames), fps))

    if args.alle:
        cols = 4
        rows = (len(ids) + cols - 1) // cols
        cell_w, cell_h = 64 * 4 + 16, 32 * 4 + 30
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (24, 24, 28))
        draw = ImageDraw.Draw(sheet)
        for i, scene_id in enumerate(ids):
            x, y = (i % cols) * cell_w + 8, (i // cols) * cell_h + 6
            small = Image.fromarray(led_look(stills[scene_id])).resize((256, 128), Image.LANCZOS)
            sheet.paste(small, (x, y))
            draw.text((x, y + 132), "%s (%s)" % (titles.get(scene_id, scene_id), scene_id), fill=(200, 200, 210))
        sheet.save(os.path.join(OUT, "alle.png"))

    if args.sprite:
        all_ids = [s[0] for s in SCENES]
        missing = [i for i in all_ids if i not in stills]
        if missing:
            sys.exit("--sprite needs every scene, missing: %s" % ", ".join(missing))
        sprite = np.concatenate([stills[i] for i in all_ids], axis=0)
        Image.fromarray(sprite).save(os.path.join(ROOT, "web", "vorschau.png"), optimize=True)
        print("web/vorschau.png: %d scenes" % len(all_ids))


if __name__ == "__main__":
    main()
