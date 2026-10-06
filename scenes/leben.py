"""Leben: Conway's Game of Life, every cell colored by its age, dying cells fade out.

A generation is computed for all cells at once with ulab in int16, spread over two frames so that
no frame gets long: first the neighbors are counted by adding shifted copies of the field (np.roll,
so the field wraps around at the edges), then the whole rule is one expression: a cell lives if
(neighbors | alive) == 3. The palette index of a living cell counts up with its age: newborn cells
are bright, old ones settle into deep colors, so the busy parts glow and the still parts rest.
When nothing changes any more or the field only repeats itself, the old world fades out and a
ring sows a new one from the middle, in new colors: random, mirrored, or a glider gun.
"""
import random

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 15
PREVIEW_AT = 3.0
GENERATION = 0.1  # seconds
TRAIL = 10  # palette 1..TRAIL: dead cells fading out, one step per frame
AGES = 40  # palette TRAIL+1 .. TRAIL+AGES: living cells by age
EDGE = TRAIL + AGES + 1  # the ring that sows a new world
MAX_GENERATIONS = 2400  # even a busy world gets replaced after four minutes
FADE_OUT = 0.7  # seconds for the old world to die away
SOW_SPEED = 26.0  # pixels per second the ring grows

THEMES = (  # newborn, young, middle aged, old, trail
    (0xB8F4FF, 0x30D8FF, 0x2070FF, 0x3A1890, 0x14306A),  # sea
    (0xFFE08C, 0xFFA418, 0xFF4020, 0x6A0E30, 0x4A1408),  # embers
    (0xD4FF9C, 0x6CF038, 0x18B060, 0x0A3A4C, 0x0E3418),  # moss
    (0xFFC4F0, 0xFF58C8, 0x9A40FF, 0x281E78, 0x3A0E3A),  # candy
)

GLIDER = (".O.", "..O", "OOO")
# Gosper's glider gun: shoots a glider every 30 generations, until its own gliders come back around
GUN = (
    "........................O...........",
    "......................O.O...........",
    "............OO......OO............OO",
    "...........O...O....OO............OO",
    "OO........O.....O...OO..............",
    "OO........O...O.OO....O.O...........",
    "..........O.....O.......O...........",
    "...........O...O....................",
    "............OO......................",
)


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * (EDGE + 1))
        self.trail = np.zeros((32, 64), dtype=np.int16)
        # distance of every pixel from the middle, for the sowing ring
        xs = (np.linspace(0, 63, 64) - 31.5).reshape((1, 64))
        ys = (np.linspace(0, 31, 32) - 15.5).reshape((32, 1))
        self.distance = np.array(np.sqrt(xs * xs + ys * ys), dtype=np.int16)
        self.theme = random.randrange(len(THEMES))
        self.history = []
        self.generations = 0
        self.clock = 0.0
        self.noise = [random.random() for _ in range(2048)]  # random numbers for the next soup
        self.sow()

    # --- Seeds ------------------------------------------------------------------------

    def soup(self, rows, cols, density):
        noise = np.array(self.noise[:rows * cols]).reshape((rows, cols))
        # floor first: ulab rounds when converting to int16, floor makes it exactly 0 or 1
        return np.array(np.floor(noise + density), dtype=np.int16)  # 1 where noise >= 1 - density

    def seed(self):
        kind = random.random()
        if kind < 0.5:
            return self.soup(32, 64, random.uniform(0.25, 0.4))
        if kind < 0.85:
            # mirrored left to right: the world stays symmetric, like a Rorschach blot
            half = self.soup(32, 32, random.uniform(0.25, 0.4))
            return np.concatenate((half, np.flip(half, axis=1)), axis=1)
        # the gun alone would always play the same film (the field wraps around, so its place
        # does not matter): a stray glider or two on the right make every run different
        field = np.zeros((32, 64), dtype=np.int16)
        self.stamp(field, GUN, 0, random.randrange(0, 32 - 9), False, False)
        for _ in range(random.randint(1, 2)):
            self.stamp(field, GLIDER, random.randrange(40, 60), random.randrange(0, 29),
                       random.random() < 0.5, random.random() < 0.5)
        return field

    def stamp(self, field, rows, x0, y0, flip_x, flip_y):
        for dy, row in enumerate(rows):
            for dx, char in enumerate(row):
                if char == "O":
                    x = x0 + (len(row) - 1 - dx if flip_x else dx)
                    y = y0 + (len(rows) - 1 - dy if flip_y else dy)
                    field[y, x] = 1

    def sow(self):
        """Start a new world: new colors, a new seed, revealed by a ring growing from the middle."""
        self.theme = (self.theme + 1 + random.randrange(len(THEMES) - 1)) % len(THEMES)
        newborn, young, middle, old, trail = THEMES[self.theme]
        # only the first generation is pale, from the second one the color is fully there
        ages = gfx.gradient(((0.0, newborn), (1.0 / (AGES - 1), young), (0.3, middle), (1.0, old)), AGES)
        trails = [gfx.scale(trail, (i / TRAIL) ** 1.5) for i in range(1, TRAIL + 1)]
        self.pal.set_all([0] + trails + ages + [gfx.mix(newborn, young, 0.3)])
        self.seeded = self.seed()
        self.alive = np.zeros((32, 64), dtype=np.int16)
        self.base = np.zeros((32, 64), dtype=np.int16)  # palette index of the living cells, 0 if dead
        self.neighbors = None
        self.radius = 0.0
        self.revealed = np.zeros((32, 64), dtype=np.int16)
        self.state = "sow"
        self.history = []
        self.generations = 0

    # --- Life -------------------------------------------------------------------------

    def count(self):
        """First half of a generation: the eight neighbors of every cell."""
        a = self.alive
        row = a + np.roll(a, 1, axis=1) + np.roll(a, -1, axis=1)
        self.neighbors = row + np.roll(row, 1, axis=0) + np.roll(row, -1, axis=0) - a

    def apply(self):
        """Second half: the rule, trails for the cells that died, colors for the living."""
        a = self.alive
        # 1 where (neighbors | alive) == 3, else 0, in plain int16 arithmetic
        new = 1 - np.minimum(abs(np.bitwise_or(self.neighbors, a) - 3), 1)
        self.neighbors = None
        # died: 1 - 0 starts a trail; born: 0 - 1 is negative and leaves the trail alone
        self.trail = np.maximum(self.trail, (a - new) * TRAIL)
        # newborn cells get TRAIL + 1, survivors count up to TRAIL + AGES, the dead get 0
        self.base = np.minimum(np.maximum(self.base + 1, TRAIL + 1), TRAIL + AGES) * new
        self.alive = new
        self.generations += 1
        self.history.append(int(np.sum(new)))
        if len(self.history) > 50:
            self.history.pop(0)

    def stuck(self):
        """True if the field is empty, or its population has repeated with a short period
        for a while: still lifes, blinkers, lone gliders flying around forever."""
        history = self.history
        if history[-1] == 0 or self.generations > MAX_GENERATIONS:
            return True
        if len(history) < 50 or self.generations % 10:
            return False
        for period in range(1, 16):
            if all(history[-i] == history[-i - period] for i in range(1, 35)):
                return True
        return False

    # --- Frames -----------------------------------------------------------------------

    def frame(self, dt):
        self.clock += dt
        if self.state == "live":
            if self.neighbors is not None:
                self.apply()
                if self.stuck():
                    self.fade_out()
            elif self.clock >= GENERATION:
                self.clock = min(self.clock - GENERATION, GENERATION)
                self.count()
        elif self.state == "sow":
            self.reveal(dt)  # life waits until the ring is through, that keeps these frames short
        elif len(self.noise) < 2048:
            # while the old world fades: random numbers for the next soup, a part per frame
            self.noise.extend([random.random() for _ in range(256)])
        elif self.clock > FADE_OUT:
            self.sow()

        self.trail = np.maximum(self.trail - 1, 0)
        index = np.maximum(self.base, self.trail)
        if self.state == "sow":
            r = int(self.radius)
            ring = np.clip(self.distance - r + 3, 0, 1) - np.clip(self.distance - r, 0, 1)  # r-2 <= d <= r
            index = np.maximum(index, ring * EDGE)
        bitmaptools.arrayblit(self.bitmap, np.array(index, dtype=np.uint8))

    def reveal(self, dt):
        """The ring grows; the part of the seed it passed comes alive (newborn)."""
        self.radius += SOW_SPEED * dt
        inside = np.clip(int(self.radius) - self.distance, 0, 1)
        fresh = (inside - self.revealed) * self.seeded
        self.revealed = inside
        self.alive = self.alive + fresh
        self.base = self.base + fresh * (TRAIL + 1)
        if self.radius > 38:
            self.state = "live"
            self.clock = 0.0

    def fade_out(self):
        """Every living cell dies at once and leaves its trail."""
        self.trail = np.maximum(self.trail, self.alive * TRAIL)
        self.base = np.zeros((32, 64), dtype=np.int16)
        self.state = "fade"
        self.clock = 0.0
        self.noise = []
