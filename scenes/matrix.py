"""Matrix-Regen: digital rain of tiny glyphs, falling at different speeds with fading green trails.

The glyphs stand still in a grid of 16 columns; what falls is the light. Every glyph cell has its
own palette entry, so the rain is pure palette animation: each frame computes how bright every
cell is (from the drops in its column) and sets the colour of its entry. Pixels are only drawn
when a glyph changes: the cell a drop reaches gets a new glyph, and now and then a glyph somewhere
in the trail flips to another one.
"""
import math
import random

from app import gfx

FPS = 30
PREVIEW_AT = 4.0

COLUMNS = 16  # 3 pixels glyph + 1 pixel gap
ROWS = 6  # 5 pixels glyph + 1 pixel gap; the top and bottom rows are cut by the edges
TOP = -2  # y of the first row
STEPS = 40  # brightness steps of the colour ramp

# 3x5 glyphs, katakana-like, a few digits and signs ("#" lit)
GLYPHS = (
    "###|..#|.#.|.#.|#..", "..#|.#.|##.|.#.|.#.", ".#.|###|#.#|..#|.#.", "###|.#.|.#.|.#.|###",
    "..#|###|.##|#.#|..#", ".#.|###|.##|#.#|#.#", ".#.|###|.#.|###|.#.", ".##|#.#|..#|.#.|#..",
    "#..|###|#.#|..#|.#.", "###|..#|..#|..#|###", "#.#|###|#.#|..#|.#.", "#..|..#|#..|..#|##.",
    "###|..#|.#.|.##|#.#", ".#.|###|.##|.#.|.##", "#.#|#.#|..#|.#.|#..", ".##|#.#|###|..#|.#.",
    "..#|##.|###|.#.|#..", "###|...|###|.#.|#..", "#..|#..|##.|#.#|#..", ".#.|###|.#.|.#.|#..",
    "###|..#|#.#|.#.|#.#", "#..|#.#|##.|#..|###", "###|..#|..#|.#.|#..", ".#.|###|.#.|###|#.#",
    "##.|..#|##.|..#|##.", ".#.|.#.|#..|#.#|###", "..#|#.#|.#.|#.#|#..", "###|.#.|###|.#.|.##",
    "#..|###|#.#|.#.|.#.", "###|..#|###|..#|###", "#.#|#.#|#.#|..#|.#.", "#..|#..|#..|#.#|##.",
    "###|#.#|..#|..#|.#.", "#..|..#|..#|.#.|#..", ".#.|##.|.#.|.#.|###", "#.#|#.#|###|..#|..#",
    "###|#..|##.|..#|##.", "...|###|...|###|...", "#.#|.#.|###|.#.|#.#", "###|..#|.#.|#..|###",
)
# brightness 0 ... 1 (the drop's head, nearly white)
RAMP = ((0.0, 0x000000), (0.12, 0x02300A), (0.35, 0x067A22), (0.62, 0x18C840), (0.85, 0x60FF84),
        (1.0, 0xE4FFE8))


class Drop:
    def __init__(self, head):
        self.speed = random.uniform(2.2, 7.0)  # rows per second
        self.head = head
        self.length = random.uniform(2.5, 9.0)  # rows of trail
        # slow drops are dimmer, as if they were farther away
        self.shine = min(1.0, 0.5 + self.speed * 0.08)


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * (1 + COLUMNS * ROWS))
        self.ramp = gfx.gradient(RAMP, STEPS)
        self.glyphs = [tuple(c == "#" for c in g.replace("|", "")) for g in GLYPHS]
        self.level = [0] * (COLUMNS * ROWS)  # ramp step shown by each cell
        self.dim = [1.0] * (COLUMNS * ROWS)  # a little irregularity in the trails
        for cell in range(COLUMNS * ROWS):
            self.new_glyph(cell)
        # it is already raining when the scene starts
        self.drops = [[Drop(random.uniform(0.0, 10.0))] if random.random() < 0.7 else [] for _ in range(COLUMNS)]
        self.wait = [random.uniform(0.5, 3.0) for _ in range(COLUMNS)]  # until the next drop
        self.t = 0.0

    def new_glyph(self, cell):
        column, row = divmod(cell, ROWS)
        x0 = column * 4
        y0 = TOP + row * 6
        pixels = random.choice(self.glyphs)
        value = 1 + cell
        bitmap = self.bitmap
        for i in range(15):
            y = y0 + i // 3
            if 0 <= y < 32:
                bitmap[x0 + i % 3, y] = value if pixels[i] else 0
        self.dim[cell] = random.uniform(0.7, 1.0)

    def frame(self, dt):
        self.t += dt
        # heavier and lighter rain in slow waves
        density = 0.8 + 0.2 * math.sin(self.t * 0.04)
        top = STEPS - 1
        for column in range(COLUMNS):
            drops = self.drops[column]
            self.wait[column] -= dt
            if self.wait[column] <= 0.0:
                drops.append(Drop(-1.0 - random.random()))  # starts above the screen
                self.wait[column] = random.uniform(0.8, 5.0) / density
            first = column * ROWS
            for drop in drops:
                before = math.floor(drop.head)
                drop.head += drop.speed * dt
                row = math.floor(drop.head)
                # the head writes a fresh glyph into every cell it reaches, and flickers a bit
                if 0 <= row < ROWS and (row != before or random.random() < 0.08):
                    self.new_glyph(first + row)
            if drops and drops[0].head - drops[0].length > ROWS + 1:
                drops.pop(0)

            for row in range(ROWS):
                light = 0.0
                for drop in drops:
                    d = drop.head - row
                    if d < -0.4:
                        continue
                    if d < 0.0:
                        b = (d + 0.4) * 2.5  # fades in just before the head arrives
                    elif d < 1.0:
                        b = 1.0
                    else:
                        b = 0.82 - (d - 1.0) / drop.length * 0.82
                        b *= self.dim[first + row]
                    b *= drop.shine
                    if b > light:
                        light = b
                level = int(light * top) if light > 0.0 else 0
                cell = first + row
                if level != self.level[cell]:
                    self.level[cell] = level
                    self.pal[1 + cell] = self.ramp[level]

        # now and then a glyph in the rain flips to another one
        if random.random() < 0.4:
            cell = random.randrange(COLUMNS * ROWS)
            if self.level[cell]:
                self.new_glyph(cell)
