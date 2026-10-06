"""Kaminfeuer: flames rising from three logs, with glowing embers.

Heat is a field of whole numbers (0-1023): every frame each pixel takes a weighted average of the
pixels below it and cools down a little. The cooling comes from a noise texture that drifts
upwards, which tears the heat into flickering flame tongues. A few hot spots wander along the
logs, so the tongues have somewhere to start. All of it with ulab in int16, for all pixels at once.
"""
import random

import bitmaptools
import displayio
from ulab import numpy as np

from app import gfx

FPS = 25
PREVIEW_AT = 3.0
ROWS = 36  # 32 visible rows plus 4 below the edge, where the heat is fed in
HOT = 1023

FIRE = ((0.0, 0x000000), (0.16, 0x2E0500), (0.34, 0x9E1500), (0.52, 0xF04A00), (0.7, 0xFF9420),
        (0.86, 0xFFCC55), (1.0, 0xFFF6D8))
WOOD = (0, 0x1E0E06, 0x3E2010, 0x6E4222, 0xB08050, 0x7A5030, 0xFF5A1F, 0xFFA040)  # 0 is transparent
DARK, MID, LIGHT, CUT, RING, EMBER, EMBER2 = 1, 2, 3, 4, 5, 6, 7


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, gfx.gradient(FIRE, 256))
        self.heat = np.zeros((ROWS, 64), dtype=np.int16)
        # cooling: soft noise 0-112, stacked twice so that a moving window never has to wrap around
        noise = np.array([[random.random() for _ in range(64)] for _ in range(64)])
        noise = (noise + np.roll(noise, 1, axis=0) + np.roll(noise, 1, axis=1) + np.roll(noise, -1, axis=1)) * 28.0
        self.cooling = np.array(np.concatenate((noise, noise)), dtype=np.int16)
        self.offset = 0
        # little cooling down at the logs, more towards the top: hot flame bodies, ragged tips (x/16)
        self.ramp = np.array([[int(24 - 20 * y / (ROWS - 3))] for y in range(ROWS - 2)], dtype=np.int16)
        # flames stand in the middle of the hearth and get lower towards the sides
        xs = np.linspace(-1.0, 1.0, 64)
        self.envelope = np.exp(-(xs * xs) * 2.5) * 0.8 + 0.2
        self.spots = np.array([random.random() for _ in range(64)])
        self.flicker = 1.0

        self.logs = displayio.Bitmap(64, 32, len(WOOD))
        self.wood = gfx.Pal(WOOD, transparent=(0,))
        group.append(displayio.TileGrid(self.logs, pixel_shader=self.wood.palette))
        self.log(9, 54, 25)
        self.log(4, 40, 28)
        self.log(26, 59, 28)
        self.embers = [(x, 24) for x in range(12, 52)] + [(x, 31) for x in range(5, 59)]

    def log(self, x0, x1, top):
        """A log lying across, 4 pixels thick, with cut ends and a little bark texture."""
        b = self.logs
        for y, value in ((top, LIGHT), (top + 1, MID), (top + 2, MID), (top + 3, DARK)):
            bitmaptools.fill_region(b, x0 + 1, y, x1, y + 1, value)
        for x in (x0, x1):
            for y in range(top, top + 4):
                b[x, y] = CUT
            b[x, top + 1] = RING
            b[x, top + 2] = RING
        for x in range(x0 + 3, x1 - 2, 5):
            b[x, top + 1 + (x // 5) % 2] = DARK

    def frame(self, dt):
        heat = self.heat
        # hot spots wander along the logs; the whole fire breathes a little
        self.spots = np.clip(self.spots + np.array([random.random() - 0.5 for _ in range(64)]) * 0.35, 0.0, 1.0)
        spots = (self.spots + np.roll(self.spots, 1) + np.roll(self.spots, -1)) * (1 / 3)
        self.flicker = min(1.08, max(0.9, self.flicker + (random.random() - 0.5) * 0.06))
        feed = np.array(np.clip((0.55 + 0.5 * spots) * self.envelope * self.flicker, 0.0, 1.0) * HOT, dtype=np.int16)
        heat[ROWS - 1] = feed
        heat[ROWS - 2] = feed

        # rise: weights 1 (left), 3 (below), 1 (right), 3 (two below), divided by 8, minus cooling
        below = heat[1:ROWS - 1]
        rising = np.right_shift(np.roll(below, 1, axis=1) + np.roll(below, -1, axis=1) + (below + heat[2:ROWS]) * 3, 3)
        self.offset = (self.offset + 1) % 64
        cooling = self.cooling[self.offset:self.offset + ROWS - 2]
        heat[0:ROWS - 2] = np.maximum(rising - np.right_shift(cooling * self.ramp, 4), 0)

        bitmaptools.arrayblit(self.bitmap, np.array(np.right_shift(heat[0:32], 2), dtype=np.uint8))

        # embers on top of the logs and on the ground glimmer
        for _ in range(8):
            x, y = self.embers[random.randrange(len(self.embers))]
            self.logs[x, y] = EMBER2 if random.random() < 0.25 else EMBER
        for _ in range(8):
            x, y = self.embers[random.randrange(len(self.embers))]
            self.logs[x, y] = 0
        self.wood[EMBER] = gfx.scale(WOOD[EMBER], 0.7 + 0.3 * random.random())
