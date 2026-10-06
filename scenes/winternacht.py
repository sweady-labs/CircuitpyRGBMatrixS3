"""Winternacht: northern lights over snowy hills, firs, a cabin with a warm window and smoke.

The aurora is a curtain of light: a sharp, wavy lower edge, from which the light fades slowly
upwards, combed into rays that drift sideways. It is computed with ulab in int16 for the sky rows
only: the lower edge and the rays are 64 values each, spread over the rows by broadcasting.
The landscape is one bitmap drawn at the start; its snow takes on a little of the aurora's color.
"""
import math
import random

import bitmaptools
import displayio
import vectorio
from ulab import numpy as np

from app import gfx

FPS = 20
PREVIEW_AT = 4.0
SKY = 23  # rows of sky the aurora is computed for
LEVELS = 40  # aurora palette: 0 night sky, then faint violet up to bright green

# two looks of the aurora that the sky blends between over a few minutes: violet tops, pink tops
AURORA = ((0.0, 0x000000), (0.12, 0x000000), (0.28, 0x1C0838), (0.45, 0x3C1670), (0.6, 0x0C5A6A),
          (0.75, 0x12A86A), (0.9, 0x34E07C), (1.0, 0x90FFB0))
AURORA_PINK = ((0.0, 0x000000), (0.12, 0x000000), (0.28, 0x300824), (0.45, 0x701850), (0.6, 0x285868),
               (0.75, 0x10B078), (0.9, 0x40F0A0), (1.0, 0xB0FFD0))
# landscape palette
(CLEAR, FIR, FIR_DARK, FIR_SNOW, CREST, SNOW, SNOW_DARK, FAR, FAR_CREST, LOG, LOG_DARK, EAVES, ROOF,
 OVERHANG, WINDOW, GLOW, DOOR, STONE, TRUNK) = range(19)
LAND = (0, 0x2A6A4C, 0x163E30, 0xC8D8F4, 0xD8E4FA, 0x8292BA, 0x5C6A94, 0x46527A, 0x7484AC, 0x8A5530,
        0x5A3418, 0x30200E, 0xA8B8DC, 0x6A7AA4, 0xFFC860, 0xD8A878, 0x2E1A0C, 0x707080, 0x3A2414)
SMOKE = (0, 0x7A8098, 0x5C6278, 0x40465C, 0x2A2E40)

FIR_SMALL = (
    "..s..",
    ".sfd.",
    ".sfd.",
    "sffdd",
    "..t..",
)
FIR_MEDIUM = (
    "...s...",
    "..sfd..",
    "..sfd..",
    ".sffdd.",
    "..sfd..",
    ".sffdd.",
    "sfffddd",
    "...t...",
)
FIR_LARGE = (
    "....s....",
    "...sfd...",
    "...sfd...",
    "..sffdd..",
    "...sfd...",
    "..sffdd..",
    ".sfffddd.",
    "..sffdd..",
    ".sfffddd.",
    "sffffdddd",
    "....t....",
)
CABIN = (
    "............kk..",
    "...cccccccccckc.",
    "..cRRRRRRRRRRRRc",
    ".cRRRRRRRRRRRRRR",
    "oooooooooooooooo",
    ".eeeeeeeeeeeeee.",
    ".LiLLLLLiLLLLiL.",
    ".lwwllllwwlddll.",
    ".LwwLLLLwwLddLL.",
    ".llllllllllddll.",
)
CABIN_KEYS = {".": CLEAR, "k": STONE, "c": CREST, "R": ROOF, "o": OVERHANG, "e": EAVES, "L": LOG,
              "l": LOG_DARK, "i": FIR_SNOW, "w": WINDOW, "d": DOOR}
FIR_KEYS = {".": CLEAR, "s": FIR_SNOW, "f": FIR, "d": FIR_DARK, "t": TRUNK}


class Scene:
    def __init__(self, group, settings):
        self.looks = (gfx.gradient(AURORA, LEVELS), gfx.gradient(AURORA_PINK, LEVELS))
        self.sky, self.sky_pal = gfx.canvas(group, self.looks[0])
        self.stars(group)
        self.land_pal = gfx.Pal(LAND, transparent=(0,))
        self.land = displayio.Bitmap(64, 32, len(LAND))
        self.landscape()
        group.append(displayio.TileGrid(self.land, pixel_shader=self.land_pal.palette))
        self.smoke_pal = gfx.Pal(SMOKE, transparent=(0,))
        self.puffs = []
        for i in range(4):
            circle = vectorio.Circle(pixel_shader=self.smoke_pal.palette, radius=1, x=0, y=-5, color_index=1)
            group.append(circle)
            self.puffs.append([circle, 0.0, 0.0, -0.2 - i * 0.8])  # shape, x, y, age (negative: waiting)
        self.flake_pal = gfx.Pal((0xFFFFFF, 0x9AA6C0))
        self.flakes = []
        for i in range(22):
            rect = vectorio.Rectangle(pixel_shader=self.flake_pal.palette, width=1, height=1, x=0, y=0,
                                      color_index=i % 2)
            group.append(rect)
            self.flakes.append([rect, random.uniform(0, 64), random.uniform(0, 32),
                                random.uniform(2.5, 5.0) * (1.0 if i % 2 == 0 else 0.6), random.uniform(0, 6.3)])

        self.rows = np.array([[4 * y] for y in range(SKY)], dtype=np.int16)  # row positions, times 4
        xs = np.linspace(0, 1, 64)
        self.waves = [xs * k for k in (5.1, 11.3, 23.0, 37.0, 71.0, 13.0)]  # phase along x of each wave
        self.t = random.uniform(0, 100)
        self.frames = 0
        self.window = 1.0  # brightness of the fire behind the windows, and where it is heading
        self.fire = 1.0

    def stars(self, group):
        """Stars above the hills, in three groups that twinkle at their own pace."""
        self.star_pal = gfx.Pal((0, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF), transparent=(0,))
        bitmap = displayio.Bitmap(64, SKY, 4)
        for i in range(30):
            bitmap[random.randrange(64), random.randrange(SKY - 4)] = 1 + i % 3
        group.append(displayio.TileGrid(bitmap, pixel_shader=self.star_pal.palette))

    def landscape(self):
        b = self.land
        # far hills with small firs, then the near slope in front of them
        far = [int(21.0 + 1.6 * math.sin(x * 0.11 + 1.0) + 0.8 * math.sin(x * 0.29)) for x in range(64)]
        for x in range(64):
            for y in range(far[x], 32):
                b[x, y] = FAR_CREST if y == far[x] else FAR
        for x, art in ((5, FIR_SMALL), (10, FIR_MEDIUM), (15, FIR_SMALL), (44, FIR_SMALL), (49, FIR_MEDIUM),
                       (61, FIR_SMALL)):
            gfx.draw_art(b, art, FIR_KEYS, x - len(art[0]) // 2, far[x] - len(art) + 2)
        self.ground = [int(27.0 - 2.2 * math.sin(x * 0.07 - 0.4) + 0.6 * math.sin(x * 0.4)) for x in range(64)]
        for x in range(64):
            near = self.ground[x]
            for y in range(near, 32):
                depth = y - near
                b[x, y] = CREST if depth == 0 else SNOW_DARK if (x * 3 + y * 7) % 11 == 0 else SNOW
        for x in (3, 24, 59):
            gfx.draw_art(b, FIR_LARGE, FIR_KEYS, x - 4, self.ground[x] - len(FIR_LARGE) + 2)
        # the cabin stands on the near slope, its windows throw warm light onto the snow
        cx = 33
        top = self.ground[cx + 8] - len(CABIN) + 1
        gfx.draw_art(b, CABIN, CABIN_KEYS, cx, top)
        for x in range(cx + 1, cx + 11):
            y = self.ground[x] + 1
            if y < 32 and (x - cx) % 8 in (1, 2, 3):
                b[x, y] = GLOW
        self.chimney = (cx + 12, top - 1)

    def aurora(self, t):
        w = self.waves
        # lower edge of the curtain in quarter rows (row 15 = 60): two slow waves and a quicker ripple
        edge = 60.0 + 10.4 * np.sin(w[0] + t * 0.21) + 5.6 * np.sin(w[1] - t * 0.37) + 2.0 * np.sin(w[2] + t * 0.9)
        # rays: brightness across the curtain, drifting sideways (about 7..17)
        rays = 12.0 + 2.2 * np.sin(w[3] + t * 0.6) + 1.5 * np.sin(w[4] - t * 1.1) + 1.8 * np.sin(w[5] + t * 0.15)
        # the whole curtain breathes slowly
        rays = rays * (0.75 + 0.25 * math.sin(t * 0.13))
        e = np.array(edge, dtype=np.int16).reshape((1, 64)) - self.rows  # quarter rows above the edge
        # sharp at the edge, fading slowly upwards (array first: 300 - e would be float in ulab)
        light = np.minimum(e * 24, e * -6 + 300)
        light = np.maximum(light, 0) * np.array(rays, dtype=np.int16).reshape((1, 64))
        index = np.minimum(np.right_shift(light, 6), LEVELS - 1)
        bitmaptools.arrayblit(self.sky, np.array(index, dtype=np.uint8), 0, 0, 64, SKY)
        return float(np.mean(rays))

    def frame(self, dt):
        self.t += dt
        t = self.t
        strength = self.aurora(t)
        # snow takes on a little green from above, the window flickers like a fire inside
        tint = min(0.3, max(0.0, (strength - 6.0) * 0.04))
        self.land_pal[CREST] = gfx.mix(LAND[CREST], 0x90FFB0, tint)
        self.land_pal[SNOW] = gfx.mix(LAND[SNOW], 0x50C080, tint)
        if random.random() < dt * 5:
            self.fire = random.uniform(0.6, 1.0)
        self.window += (self.fire - self.window) * min(1.0, dt * 8)
        self.land_pal[WINDOW] = gfx.mix(0xC05010, 0xFFD070, self.window)
        self.land_pal[GLOW] = gfx.mix(LAND[SNOW], 0xFFC890, self.window * 0.7)
        for i in range(3):
            self.star_pal[1 + i] = gfx.scale(0xE8F0FF, 0.55 + 0.45 * math.sin(t * (1.1 + 0.4 * i) + i * 2.0))
        # every few seconds the sky moves a step between its two looks (a full swing takes 4 minutes)
        self.frames += 1
        if self.frames % 40 == 0:
            blend = 0.5 - 0.5 * math.cos(t * 2 * math.pi / 240)
            violet, pink = self.looks
            self.sky_pal.set_all([gfx.mix(a, b, blend) for a, b in zip(violet, pink)])
        self.smoke(dt)
        self.snow(dt)

    def smoke(self, dt):
        """Puffs rise from the chimney, drift with the wind and fade."""
        x0, y0 = self.chimney
        wind = 1.5 + 1.0 * math.sin(self.t * 0.2)
        for puff in self.puffs:
            circle = puff[0]
            puff[3] += dt
            age = puff[3]
            if age < 0:
                circle.hidden = True
                continue
            if age > 3.2:
                puff[1], puff[2], puff[3] = float(x0), float(y0), 0.0
                age = 0.0
            puff[1] += wind * dt * min(1.0, age)
            puff[2] -= 2.2 * dt
            circle.hidden = False
            circle.x = int(puff[1])
            circle.y = int(puff[2])
            circle.color_index = min(4, 1 + int(age * 1.2))

    def snow(self, dt):
        drift = 1.5 * math.sin(self.t * 0.17)
        for f in self.flakes:
            f[2] += f[3] * dt
            f[4] += dt
            if f[2] >= 32:
                f[2] -= 33
                f[1] = random.uniform(0, 64)
            f[0].x = int(f[1] + drift + 1.2 * math.sin(f[4]))
            f[0].y = int(f[2])
