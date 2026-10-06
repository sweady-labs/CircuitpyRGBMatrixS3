"""Plasma: overlapping sine waves, computed for all pixels at once with ulab.

To stay fast, most waves run along x or y only (64 or 32 values) and are spread over the screen
by broadcasting. Only the ripple around a wandering center needs the whole screen: its sine is
computed once for a field twice the size of the screen, and every frame looks through a window
into it. The color scheme changes every THEME_SECONDS and blends softly into the next one.
"""
import math

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 25
PREVIEW_AT = 2.0
THEME_SECONDS = 40
BLEND_SECONDS = 4

# cyclic gradients (first color == last color), so the colors can flow endlessly
THEMES = (
    ((0.0, 0x0B1E5B), (0.3, 0x1B8CD8), (0.5, 0x7DF9FF), (0.7, 0x1B8CD8), (1.0, 0x0B1E5B)),  # ocean
    ((0.0, 0x3A0CA3), (0.25, 0xF72585), (0.5, 0xFFB703), (0.75, 0xF72585), (1.0, 0x3A0CA3)),  # sunset
    ((0.0, 0x00F5D4), (0.33, 0x9B5DE5), (0.66, 0xF15BB5), (1.0, 0x00F5D4)),  # neon
    ((0.0, 0x0B3D20), (0.3, 0x2DC653), (0.55, 0xD8F3DC), (0.8, 0x2DC653), (1.0, 0x0B3D20)),  # forest
)


class Scene:
    def __init__(self, group, settings):
        self.themes = [gfx.gradient(stops, 256) for stops in THEMES]
        self.theme = 0
        self.bitmap, self.pal = gfx.canvas(group, self.themes[0])
        self.xs = np.linspace(0, 1, 64)
        self.ys = np.linspace(0, 0.5, 32)
        # ripple field, twice the screen: sin and cos of the distance from its middle, times 30
        yy = np.linspace(-0.5, 0.5, 64).reshape((64, 1))
        xx = np.linspace(-1.0, 1.0, 128).reshape((1, 128))
        distance = np.sqrt(xx * xx + yy * yy) * 16.0
        self.ripple_sin = np.sin(distance) * 30.0
        self.ripple_cos = np.cos(distance) * 30.0
        self.t = 0.0
        self.shift = 0.0
        self.theme_time = 0.0
        self.frames = 0

    def frame(self, dt):
        self.t += dt
        t = self.t
        # waves along x and y, and one that is the product of both (values -32..32 each)
        wave_x = (np.sin(self.xs * 9.0 + t * 0.9) * 32.0).reshape((1, 64))
        wave_y = (np.sin(self.ys * 13.0 - t * 0.7) * 32.0).reshape((32, 1))
        cross_x = (np.sin(self.xs * 7.0 + t * 0.5) * 32.0).reshape((1, 64))
        cross_y = np.cos(self.ys * 7.0 - t * 0.3).reshape((32, 1))
        v = wave_x + wave_y + cross_x * cross_y

        # ripple: window into the field, sin(d - phase) = sin(d) cos(phase) - cos(d) sin(phase)
        ox = int(32 + 22 * math.sin(t * 0.31))
        oy = int(16 + 10 * math.cos(t * 0.23))
        phase = t * 1.3
        v = v + self.ripple_sin[oy:oy + 32, ox:ox + 64] * math.cos(phase)
        v = v - self.ripple_cos[oy:oy + 32, ox:ox + 64] * math.sin(phase)

        # -126..126 -> 1..253, then shifted over time so the colors flow (uint8 wraps around)
        index = np.array(v + 127.0, dtype=np.uint8)
        self.shift = (self.shift + dt * 22.0) % 256
        bitmaptools.arrayblit(self.bitmap, index + int(self.shift))
        self.change_theme(dt)

    def change_theme(self, dt):
        self.theme_time += dt
        if self.theme_time < THEME_SECONDS:
            return
        self.frames += 1
        blend = (self.theme_time - THEME_SECONDS) / BLEND_SECONDS
        new = self.themes[(self.theme + 1) % len(self.themes)]
        if blend >= 1.0:
            self.theme = (self.theme + 1) % len(self.themes)
            self.theme_time = 0.0
            self.pal.set_all(new)
        elif self.frames % 3 == 0:  # blending 256 colors costs time, every third frame is enough
            old = self.themes[self.theme]
            self.pal.set_all([gfx.mix(a, b, blend) for a, b in zip(old, new)])
