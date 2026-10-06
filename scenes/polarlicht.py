"""Polarlicht: a green curtain of light with violet fringes waves slowly over stars and snowy mountains.

The curtain is described by three rows of 64 numbers: where its lower edge is in every column, how
far its rays reach above it and how bright they are. They come from wave textures that are
computed once and are only looked at through moving windows every frame (sliced views, nothing to
compute). Broadcasting spreads them over the sky: every pixel lights up sharply just above the
edge and fades upwards to the top of its ray, all in int16. The palette turns brightness into
color, in eight bands from the top of the sky down: bright light is green everywhere, faint light
is pink and violet high up and teal further down, like the aurora in photos.
"""
import math
import random

import bitmaptools
import displayio
from ulab import numpy as np

from app import gfx

FPS = 20
PREVIEW_AT = 8.0
SKY = 24  # rows with aurora; the mountains hide everything below
BANDS = 8  # the palette has 8 bands of 3 rows, with 32 brightness steps each
FAINT = 3  # the faintest steps stay transparent, so the stars shine through
TEXTURE = 256  # the wave textures repeat after this many pixels ...
SUB = 4  # ... and are sampled in quarter pixels, so they move smoothly
RISE = 48  # brightness gained per quarter pixel above the lower edge: a sharp edge

# color of faint and of medium light, from the top band of the sky to the bottom one
FAINT_LIGHT = ((0.0, 0x701858), (0.3, 0x40287C), (0.6, 0x104A68), (1.0, 0x0E5C30))
MEDIUM_LIGHT = ((0.0, 0x5048B0), (0.25, 0x2090A0), (0.5, 0x18B078), (1.0, 0x1CB458))
STARS = (0x8C98B0, 0xFFF4E0, 0xB8D0FF, 0xFFD8A0, 0x8C98B0, 0xB8D0FF)
ROCK, SNOW, FOREST, RIDGE = 1, 2, 3, 4


def texture(waves, scale):
    """Periodic wave as int16, -scale..scale: waves = ((cycles per TEXTURE, amplitude), ...).
    64 extra pixels at the end, so that any window can be read without wrapping around."""
    n = TEXTURE * SUB
    xs = np.linspace(0, 2 * math.pi * (n + 64 * SUB) / n, n + 64 * SUB, endpoint=False)
    total = np.zeros(n + 64 * SUB)
    for cycles, amplitude in waves:
        total = total + np.sin(xs * cycles + random.uniform(0, 6.3)) * amplitude
    return np.array(total * (scale / np.max(abs(total))), dtype=np.int16)


class Scene:
    def __init__(self, group, settings):
        # stars, each with one of a few colors that twinkle independently
        stars, self.star_pal = gfx.canvas(group, (0,) + STARS)
        for _ in range(45):
            stars[random.randrange(64), random.randrange(22)] = random.randrange(1, len(STARS) + 1)
        self.twinkle = [(random.uniform(0.8, 2.0), random.uniform(0, 6.3)) for _ in STARS]

        colors = []
        for faint, medium in zip(gfx.gradient(FAINT_LIGHT, BANDS), gfx.gradient(MEDIUM_LIGHT, BANDS)):
            colors += gfx.gradient(((0.0, 0), (0.1, faint), (0.35, medium), (0.6, 0x20D868), (0.8, 0x40FF60),
                                    (1.0, 0xA8FFA0)), 32)
        self.aurora = displayio.Bitmap(64, SKY, 256)
        pal = gfx.Pal(colors, transparent=[band * 32 + i for band in range(BANDS) for i in range(FAINT)])
        group.append(displayio.TileGrid(self.aurora, pixel_shader=pal.palette))

        self.land = displayio.Bitmap(64, 32, 5)
        # transparent, rock, snow (tinted by the aurora every frame), forest, the ridge against the sky
        self.land_pal = gfx.Pal((0, 0x0C1C34, 0x34485C, 0x000000, 0x1C3048), transparent=(0,))
        group.append(displayio.TileGrid(self.land, pixel_shader=self.land_pal.palette))
        self.draw_land()

        # rows in quarter pixels, and times RISE, as columns for broadcasting
        self.rows4 = np.array([[y * 4] for y in range(SKY)], dtype=np.int16)
        self.rows_rise = self.rows4 * RISE
        self.band = np.array([[y // 3 * 32] for y in range(SKY)], dtype=np.int16)  # palette band per row
        # in quarter pixels: slow swells move the lower edge, finer waves the tops of the rays,
        # streaks (brightness per column) are the rays
        self.swell = texture(((2, 1.0), (3, 0.8), (5, 0.5), (8, 0.25)), 16)
        self.tops = texture(((5, 1.0), (9, 0.7), (14, 0.5)), 12)
        self.streaks = texture(((23, 1.0), (37, 0.8), (53, 0.7), (71, 0.5)), 6)
        self.t = 0.0
        self.activity = 0.8
        self.target = 0.9

    def window(self, wave, speed, phase=0.0):
        """64 values of a texture, seen through a window that moves with speed (pixels per second)."""
        offset = int((self.t * speed + phase) * SUB) % (TEXTURE * SUB)
        return wave[offset:offset + 64 * SUB:SUB]

    def frame(self, dt):
        self.t += dt
        # now and then the activity drifts towards a new goal: brighter and taller, or calmer
        if random.random() < dt / 12.0:
            self.target = random.uniform(0.5, 1.0)
        self.activity += (self.target - self.activity) * min(1.0, dt * 0.25)

        # all in quarter pixels per column: lower edge, how far the rays reach, their brightness.
        # The rays drift along the curtain and the brighter ones reach higher; a slow swell darkens
        # parts of it, and over minutes the whole curtain rises and sinks.
        streaks = self.window(self.streaks, 3.5) + self.window(self.streaks, -2.2, 60.0)
        base = int(48 + 10 * math.sin(self.t * 0.02))
        edge = self.window(self.swell, 1.2) + self.window(self.swell, -0.8, 100.0) + base
        top = edge - self.window(self.tops, 2.0) - streaks - int(16 + 10 * self.activity)
        gain = np.maximum(streaks + self.window(self.swell, 0.9, 200.0) * 2 + int(20 + 14 * self.activity), 0)

        # rises steeply from one pixel below the edge, fades to 0 at the top of each ray
        rise = (edge * RISE + 4 * RISE).reshape((1, 64)) - self.rows_rise
        fade = np.right_shift((self.rows4 - top.reshape((1, 64))) * gain.reshape((1, 64)), 2)
        light = np.right_shift(np.clip(np.minimum(rise, fade), 0, 255), 3)
        bitmaptools.arrayblit(self.aurora, np.array(light + self.band, dtype=np.uint8))

        for i, (speed, phase) in enumerate(self.twinkle):
            self.star_pal[i + 1] = gfx.scale(STARS[i], 0.75 + 0.25 * math.sin(self.t * speed + phase))
        # the snow on the peaks catches a little of the green light
        self.land_pal[SNOW] = gfx.mix(0x34485C, 0x3C6458, self.activity)

    def draw_land(self):
        """Mountains a little lighter than the night, snow on the peaks, a black spruce forest in front."""
        b = self.land
        peaks = ((3, 17, 0.8), (19, 11, 0.75), (31, 15, 0.9), (45, 13, 0.7), (60, 16, 0.85))
        notches = "0010200100120010002101000120010020100010021000102001001200100010"
        for x in range(64):
            ridge = min(24, min(int(top + slope * abs(x - px)) for px, top, slope in peaks) + int(notches[x]))
            for y in range(ridge, 32):
                b[x, y] = ROCK
            b[x, ridge] = RIDGE  # a faint edge against the sky
            for y in range(ridge, min(16, ridge + 3 - (x % 4 == 1))):
                b[x, y] = SNOW
        bitmaptools.fill_region(b, 0, 27, 64, 32, FOREST)
        x = random.randint(0, 2)
        while x < 64:
            self.spruce(x, random.randint(27, 29), random.randint(5, 10))
            x += random.randint(2, 5)

    def spruce(self, x, base, height):
        """A spruce: pointed tip, widening downwards in tiers of branches."""
        tip = base - height
        for i in range(height):
            half = i // 3 + (i % 3) // 2
            for dx in range(-half, half + 1):
                if 0 <= x + dx < 64:
                    self.land[x + dx, tip + i] = FOREST
