# Writing a scene

A scene is one module in this folder, registered in `scenes/__init__.py` as `(id, title, group)`.
The engine (`app/engine.py`) imports it when it is shown and unloads it afterwards.

```python
"""Short description of what you see."""
from app import gfx

FPS = 30          # frames per second the engine asks for (optional, default 30)
PREVIEW_AT = 3.0  # second of the still picture in the web interface (optional)


class Scene:
    def __init__(self, group, settings):
        # build all layers here and append them to group (a displayio.Group)
        self.bitmap, self.pal = gfx.canvas(group, [0x000000, 0xFF8800])

    def frame(self, dt):
        # dt: seconds since the last frame. Move things by speed * dt, never by "one step per frame".
        ...
```

The display is 64 x 32 pixels. `settings` is the settings dict (`settings["message"]` holds the text
of the Laufschrift); most scenes ignore it.

## Colors

Always go through `gfx`, never create a `displayio.Palette` yourself:

- `gfx.canvas(group, colors, transparent=())` – full screen bitmap plus its `gfx.Pal`.
- `gfx.Pal(colors, transparent=(0,))` – palette for your own bitmaps, TileGrids and vectorio
  shapes (`pixel_shader=pal.palette`). `pal[i] = color` changes a color (cheap, ~5 µs).
- Colors are `0xRRGGBB` as they should *look*, like on a computer screen. `gfx` adds gamma
  correction for the LEDs and the brightness (night mode). So design colors on a screen and they
  come out right; don't pre-darken them.
- Helpers: `gfx.hsv(h, s, v)`, `gfx.mix(a, b, t)`, `gfx.scale(color, f)`, `gfx.gradient(stops, n)`.

Palette animation (changing colors instead of pixels) is the cheapest animation there is.

## Drawing tools

- Text: `gfx.Label(group, "Text", color, x, y, center=False)` or `gfx.draw_text(bitmap, text, x, y, value)`.
  Font `app/font.py`: `NORMAL` (cap height 7, umlauts), `BIG` (clock digits 10x16), `ICONS`.
- Pixel art: `gfx.art_bitmap(rows, {".": 0, "r": 1})`, `gfx.draw_art(...)`, `gfx.sprite_sheet(frames, colors)`
  (all frames of an animation in one bitmap; `grid[0] = n` switches frames for free).
- `vectorio.Circle/Rectangle/Polygon(pixel_shader=pal.palette, ...)`: moving them (`.x`, `.y`) is almost free.
- `displayio.TileGrid` moved by `.x`/`.y`, `displayio.Group(scale=2)` for big chunky pixels.
- `bitmaptools`: `fill_region`, `draw_line`, `draw_circle`, `blit`, `arrayblit`, `draw_polygon`.
- `ulab.numpy` for full screen effects, then `bitmaptools.arrayblit(bitmap, uint8_array)`.

## What things cost on the device

Measured on the MatrixPortal S3 (ESP32-S3). The budget of a frame at 25 fps is 40 ms, and the
display refresh already takes up to 7 ms of it (only for the parts that changed). Aim for at most
about 25 ms of your own work per frame, otherwise lower `FPS`.

| Operation | Time |
| --- | --- |
| one ulab float op on all 2048 pixels (add, multiply) | 1.5 ms |
| `np.sin`/`np.cos` on 2048 floats | 3 ms |
| float array -> uint8 (`np.array(a, dtype=np.uint8)`) | 5 ms |
| one ulab int16 op on 2048 values (add, shift, maximum) | 0.6 ms |
| int16 -> uint8 | 1.8 ms |
| uint8 add (wraps around at 256) | 0.4 ms |
| `np.roll` 32x64 int16 / 64x64 float | 1 ms / 6.5 ms |
| ulab op on a 64 or 32 long 1D array | 0.2 ms |
| `bitmaptools.arrayblit` full screen | 0.55 ms |
| `bitmaptools.fill_region` full screen / `bitmap.fill` | 0.5 ms / 0.05 ms |
| `draw_line`, `blit` 16x16 | 0.05 ms, 0.2 ms |
| moving 30 vectorio shapes | 0.2 ms |
| setting 256 palette colors | 1.3 ms |
| Python: setting 2048 pixels one by one | 16 ms (never per frame!) |
| Python: simple loop, per iteration | ~3 µs |

So: full screen effects in ulab, preferably int16; waves along x or y as 1D arrays spread by
broadcasting (`a.reshape((1, 64)) + b.reshape((32, 1))`); precompute what does not change; draw
sprites and shapes instead of pixels; animate palettes.

## Device limits the simulator also checks

- ulab: no `%` on arrays, no indexing with integer arrays, Boolean mask assignment only on 1D
  arrays, no `np.random`, no `np.abs` (use `abs()`), no `np.mod`, no `np.hypot`. Arrays made from
  lists are float32. Converting to uint8/int16 fails if a value does not fit: clip first.
  In-place operators that would broadcast (`a += b` with a smaller `a`) fail; write `a = a + b`.
- `bitmaptools.fill_region` raises for coordinates outside the bitmap (draw_line and draw_circle clip).
  `draw_polygon` needs `array.array("h", ...)`, not lists.
- `math` has no `hypot`, `tau`, `isclose`, `dist`. `random` only has `random`, `randint`,
  `randrange`, `uniform`, `choice`, `getrandbits`, `seed` (no `shuffle`, no `gauss`).
- Don't read the clock for animation; use `dt`. For date-aware scenes, `app.clock.now()` gives the
  local time as `struct_time`, or `None` while the clock is not synced yet.

## Look and feel

- It is an LED panel in a hallway: black is "off", so dark backgrounds with saturated colors look
  best. Avoid large white areas.
- Calm and continuous: scenes run for hours. No strobing or fast full-screen flashes. Vary over
  time (randomness, slow cycles), so a scene does not visibly repeat after a few seconds.
- Crisp pixel art beats blurry detail. Small sprites with clear outlines read from a distance.
- Check it also at low brightness: `--hell 15` in the preview.

## Preview and tests on a computer

```bash
python3 -m venv .venv && .venv/bin/pip install numpy pillow
.venv/bin/python tools/vorschau.py plasma           # vorschau/plasma.gif and vorschau/plasma.png
.venv/bin/python tools/vorschau.py --alle           # every scene, plus vorschau/alle.png
.venv/bin/python -m unittest discover tests         # every scene runs without errors
```

The simulator (`tools/sim`) imitates displayio, bitmaptools, vectorio and ulab, including the
limits above. Colors in the previews are simulated like the LEDs show them.
