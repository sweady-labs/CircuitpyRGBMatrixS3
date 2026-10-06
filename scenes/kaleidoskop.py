"""Kaleidoskop: a sixfold, mirrored pattern of colored glass turns slowly, blossoms outwards and changes shape.

The pattern is a sum of waves around the middle: cos(6(a - turn)) and cos(12(a - turn)), where a
is the angle of a pixel seen from the middle, plus rings cos(k r - phase) running outwards (r is
the distance from the middle). Each of these is mirror symmetric around the turned axes, so the
sum is too. With cos(u - v) = cos u cos v + sin u sin v every wave splits into fields that never
change (computed once, int16) times numbers that do: a frame is six multiply-adds on whole arrays.
The distance is added as well, so the colors flow outwards while the palette index runs along.
bitwise_and wraps the index around a closed loop of colors, and the palette darkens towards the
edges in eight steps, like looking into a tube.
"""
import math

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 15
PREVIEW_AT = 4.0
FOLD = 6  # mirror axes
HUES = 32  # colors around the loop; the palette has 8 brightness steps of them
THEME_SECONDS = 45
BLEND_SECONDS = 5
VIGNETTE = (1.0, 1.0, 0.95, 0.85, 0.72, 0.58, 0.45, 0.34)  # brightness from the middle outwards

# closed loops of colors (first == last); the dark steps between them look like the lead of glass
THEMES = (
    ((0.0, 0x000000), (0.08, 0xE0115F), (0.24, 0xFFA000), (0.33, 0x000000), (0.42, 0x00C878), (0.58, 0x1E5AFF),
     (0.67, 0x000000), (0.75, 0x9B30FF), (0.91, 0xFF5AC8), (1.0, 0x000000)),  # jewels
    ((0.0, 0x000000), (0.08, 0x00E5FF), (0.24, 0x1450FF), (0.33, 0x000000), (0.42, 0x8A40FF), (0.58, 0x30FFD0),
     (0.67, 0x000000), (0.75, 0x0090FF), (0.91, 0xD8F0FF), (1.0, 0x000000)),  # ice
    ((0.0, 0x000000), (0.08, 0xFF2A6A), (0.24, 0xFF9A1A), (0.33, 0x000000), (0.42, 0xFFE040), (0.58, 0xE01890),
     (0.67, 0x000000), (0.75, 0x8C20FF), (0.91, 0xFF6040), (1.0, 0x000000)),  # sunset
    ((0.0, 0x000000), (0.08, 0x9CFF20), (0.24, 0x00B890), (0.33, 0x000000), (0.42, 0xFFD020), (0.58, 0x30E060),
     (0.67, 0x000000), (0.75, 0x00A0E0), (0.91, 0xD8FF80), (1.0, 0x000000)),  # spring
)


def palette(stops):
    loop = gfx.gradient(stops, HUES + 1)[:HUES]  # the last color equals the first
    return [gfx.scale(color, light) for light in VIGNETTE for color in loop]


class Scene:
    def __init__(self, group, settings):
        self.themes = [palette(stops) for stops in THEMES]
        self.theme = 0
        self.bitmap, self.pal = gfx.canvas(group, self.themes[0])

        xs = np.linspace(-31.5, 31.5, 64).reshape((1, 64))
        ys = np.linspace(-15.5, 15.5, 32).reshape((32, 1))
        r = np.sqrt(xs * xs + ys * ys)
        a = np.arctan2(ys + xs * 0.0, xs + ys * 0.0) * FOLD  # both broadcast to the full screen first
        petals = r * np.exp(r * -0.085) * 13.0  # strongest halfway out, calmer at the edges
        lace = np.sin(r * 0.32) * np.exp(r * -0.05) * 40.0  # inner and outer parts turn opposite ways

        def field(values):
            return np.array(values, dtype=np.int16)

        self.fields = (field(np.cos(a) * petals), field(np.sin(a) * petals),
                       field(np.cos(a * 2.0) * lace), field(np.sin(a * 2.0) * lace),
                       field(np.cos(r * 0.42) * 40.0), field(np.sin(r * 0.42) * 40.0))
        self.distance = field(r * 4.0)
        # palette block per pixel: brightness step by distance from the middle (floor, because
        # converting to int16 would round)
        self.vignette = field(np.floor(np.clip(r / 4.4 - 1.0, 0.0, 7.0))) * HUES
        self.t = 0.0
        self.turn = 0.0
        self.flow = 0.0
        self.theme_time = 0.0
        self.frames = 0

    def frame(self, dt):
        self.t += dt
        t = self.t
        self.turn += dt * (0.08 + 0.06 * math.sin(t * 0.017))  # radians, never quite the same speed
        turn = FOLD * self.turn
        # the strengths of the waves drift slowly, so the motif keeps changing
        petals = 40 + 20 * math.sin(t * 0.07)
        lace = 22 + 22 * math.sin(t * 0.053 + 1.0)
        rings = 18 + 16 * math.sin(t * 0.041 + 2.0)
        weights = (petals * math.cos(turn), petals * math.sin(turn),
                   lace * math.cos(2 * turn), lace * math.sin(2 * turn),
                   rings * math.cos(t * 0.9), rings * math.sin(t * 0.9))
        waves = self.fields[0] * int(weights[0])
        for f, w in zip(self.fields[1:], weights[1:]):
            waves = waves + f * int(w)
        self.flow = (self.flow + dt * 16.0) % 256
        value = np.right_shift(waves, 6) + self.distance + (255 - int(self.flow))
        hue = np.bitwise_and(np.right_shift(value, 3), HUES - 1)
        bitmaptools.arrayblit(self.bitmap, np.array(hue + self.vignette, dtype=np.uint8))
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
