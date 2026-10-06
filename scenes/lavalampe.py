"""Lavalampe: soft blobs of wax rise from a warm pool, merge, part and sink again; the colors change slowly.

The blobs are metaballs: every blob adds a soft bump to a field, and where the sum is high
enough you see wax. Computing a bump per pixel would be expensive, so it is computed once per
blob size as a picture twice as large as the screen; a blob at (x, y) only adds the 32 x 64
window of that picture which puts the bump in the right place (a sliced view, then one int16
add). The palette turns the field into color: dark liquid, a glow around the wax, a sharp rim
and a light core. Where two bumps overlap, the sum bridges the gap and the blobs flow into one.
"""
import math
import random

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 20
PREVIEW_AT = 6.0
EDGE = 110  # field value of the wax surface (one blob alone reaches 255 in its middle)
THEME_SECONDS = 60
BLEND_SECONDS = 8

# (liquid, wax rim, wax core)
THEMES = (
    (0x0C0206, 0xFF3C0A, 0xFFC860),  # orange lava in dark red
    (0x070210, 0xE0209C, 0xFFB0F0),  # magenta in violet
    (0x041640, 0x10B4EC, 0xB0F6FF),  # cyan in deep blue
    (0x340A44, 0xFF7020, 0xFFD890),  # orange in purple
    (0x020802, 0x60E018, 0xEEFF98),  # lime in dark green
)

POOL = 16  # kernel radius of the two bumps that form the pool at the bottom
# (kernel radius, x, horizontal swing, vertical period in seconds) of the blobs that travel;
# only two sizes, every size needs its own kernel (about 12 KB)
BLOBS = ((11, 12, 6, 41), (8, 27, 8, 29), (8, 44, 5, 23), (11, 53, 7, 53), (11, 34, 9, 37))


def kernel(radius):
    """The bump of one blob: (1 - (d / radius)^2)^3 * 255, zero outside, as uint8 with room for
    any position of the blob on (or a little off) the screen. Its middle is at row 31 + radius,
    column 63 + radius."""
    xs = np.linspace(-(63 + radius), 63 + radius, 127 + 2 * radius).reshape((1, 127 + 2 * radius))
    ys = np.linspace(-(31 + radius), 31 + radius, 63 + 2 * radius).reshape((63 + 2 * radius, 1))
    inside = np.clip(1.0 - (xs * xs + ys * ys * 0.8) / (radius * radius), 0.0, 1.0)  # a little taller than wide
    return np.array(inside * inside * inside * 255.0, dtype=np.uint8)


def palette(theme):
    """Field value 0..255 -> color: liquid, a glow of the wax color, the rim, a light core."""
    liquid, rim, core = theme
    glow = gfx.mix(liquid, rim, 0.3)
    e = EDGE / 255
    return gfx.gradient(((0.0, liquid), (0.13, gfx.mix(liquid, glow, 0.4)), (e - 0.1, glow),
                         (e - 0.025, gfx.mix(glow, rim, 0.5)), (e + 0.02, rim), (0.8, gfx.mix(rim, core, 0.25)),
                         (0.95, gfx.mix(rim, core, 0.75)), (1.0, core)), 256)


class Scene:
    def __init__(self, group, settings):
        self.themes = [palette(theme) for theme in THEMES]
        self.theme = random.randrange(len(THEMES))
        self.bitmap, self.pal = gfx.canvas(group, self.themes[self.theme])
        self.kernels = {}
        for radius in set(b[0] for b in BLOBS) | {POOL}:
            self.kernels[radius] = kernel(radius)
        # warm light from the bottom of the lamp: the liquid glows a little there
        self.light = np.array([[int(34 * (y / 31) ** 2)] for y in range(32)], dtype=np.int16)
        self.phases = [random.uniform(0, 2 * math.pi) for _ in BLOBS]
        self.t = 0.0
        self.theme_time = 0.0
        self.frames = 0

    def add(self, field, radius, x, y):
        """field + the bump of a blob at (x, y); positions off the screen are fine."""
        k = self.kernels[radius]
        x = min(63 + radius, max(-radius, int(x)))
        y = min(31 + radius, max(-radius, int(y)))
        cx, cy = 63 + radius, 31 + radius
        return field + k[cy - y:cy - y + 32, cx - x:cx - x + 64]

    def frame(self, dt):
        self.t += dt
        t = self.t
        # the pool of warm wax at the bottom, slowly heaving
        field = self.add(self.light, POOL, 16 + 4 * math.sin(t * 0.11), 37 + 1.5 * math.sin(t * 0.37))
        field = self.add(field, POOL, 48 + 4 * math.sin(t * 0.13 + 2.0), 37 + 1.5 * math.sin(t * 0.29 + 1.0))
        # blobs: rise from the pool, linger at the top, sink back (slowest at both ends, like real wax)
        for (radius, x, swing, period), phase in zip(BLOBS, self.phases):
            p = t * 2 * math.pi / period + phase
            y = 15.5 - 21.0 * math.cos(p)
            x = x + swing * math.sin(p * 0.5 + phase) + 2.0 * math.sin(t * 0.23 + phase)
            field = self.add(field, radius, x, y)
        bitmaptools.arrayblit(self.bitmap, np.array(np.minimum(field, 255), dtype=np.uint8))
        self.change_theme(dt)

    def change_theme(self, dt):
        self.theme_time += dt
        if self.theme_time < THEME_SECONDS:
            return
        blend = (self.theme_time - THEME_SECONDS) / BLEND_SECONDS
        old = self.themes[self.theme]
        new = self.themes[(self.theme + 1) % len(self.themes)]
        if blend >= 1.0:
            self.theme = (self.theme + 1) % len(self.themes)
            self.theme_time = 0.0
            self.pal.set_all(new)
            return
        # blending 256 colors costs time: a third of them per frame keeps every frame equally fast
        self.frames += 1
        for i in range(self.frames % 3, len(new), 3):
            self.pal[i] = gfx.mix(old[i], new[i], blend)
