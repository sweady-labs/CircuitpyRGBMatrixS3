"""Feuerwerk: rockets rise over a city at night and burst into peonies, rings, willows and crackles.

Every spark is a small list [x, y, vx, vy, seconds left, life, colour, kind, trail] moved with
gravity and air drag. The sky layer is cleared every frame and all sparks are drawn again: the
spark itself and the last pixels it passed, dimmer and dimmer, as its trail. Because the trail
remembers pixels and not frames, slow sparks (the drooping gold of a willow) leave long trails and
fast ones dotted streaks. The skyline is a layer on top, so sparks sink behind the houses. Every
burst lights up the city: its colour tints the roof edges and the walls for a moment (palette only).
"""
import math
import random

import bitmaptools
import displayio

from app import gfx

FPS = 20
PREVIEW_AT = 3.4

GRAVITY = 9.0  # pixels per second squared
LEVELS = 8  # brightness steps per colour
# (dim, bright) of every colour family; the bright one is also the light the burst throws
FAMILIES = (
    (0xA01008, 0xFF6A50),  # red
    (0xB03A00, 0xFFA040),  # orange
    (0x9A5A00, 0xFFE070),  # gold
    (0x0A8A20, 0x80FF80),  # green
    (0x0A70A0, 0x90F0FF),  # cyan
    (0x2030C0, 0x9AB0FF),  # blue
    (0x6A10B0, 0xD890FF),  # purple
    (0xB0106A, 0xFF90D0),  # pink
    (0x606878, 0xFFFFFF),  # silver
)
GOLD, SILVER = 2, 8
MAX_SPARKS = 150  # no new rockets above this, it keeps the frame time in check

# kinds of sparks, and for each kind: air drag per second, share of the gravity, and how much
# dimmer the pixels of its trail are, from the oldest to the spark itself
STAR, CRACKLE, WILLOW, EMBER = 0, 1, 2, 3
DRAG = (1.2, 1.2, 1.6, 1.2)
FALL = (1.0, 1.0, 0.45, 1.0)
TRAIL_DIMS = ((5, 2, 0), (3, 0), (6, 5, 4, 3, 2, 2, 1, 0), (0,))
SHELLS = ("peony", "peony", "double", "ring", "willow", "crackle")

# skyline layer: faint dark blue houses, a little lighter at the roof edges
WALL, RIM, WINDOW, WINDOW2 = 1, 2, 3, 4
CITY_TOP = 16  # y of the skyline layer
WALL_COLOR = 0x0E1636
RIM_COLOR = 0x1A2650


def family_colors(dim, bright):
    colors = []
    for level in range(LEVELS):
        share = level / (LEVELS - 1)
        colors.append(gfx.scale(gfx.mix(dim, bright, share), 0.3 + 0.7 * share))
    return colors


class Scene:
    def __init__(self, group, settings):
        colors = [0]
        for dim, bright in FAMILIES:
            colors.extend(family_colors(dim, bright))
        self.bitmap, self.pal = gfx.canvas(group, colors, transparent=(0,))

        self.city_pal = gfx.Pal([0, 0, 0, 0xB07A30, 0x8890A8], transparent=(0,))
        city = displayio.Bitmap(64, 32 - CITY_TOP, 5)
        self.build_city(city)
        group.append(displayio.TileGrid(city, pixel_shader=self.city_pal.palette, y=CITY_TOP))

        self.sparks = []
        self.rockets = []  # [x, y, vx, vy, shell, family]
        self.wait = 0.3  # until the next rocket
        self.salvo = 1  # rockets left in a quick series: two to open the show
        self.light = 0.0  # light of the last burst on the city, 0 ... 1
        self.light_color = 0
        self.light_city()

    def build_city(self, city):
        """Houses of random width and height side by side, a few windows still lit."""
        h = city.height
        x = random.randint(-3, 0)
        while x < 64:
            width = random.randint(4, 9)
            height = random.randint(3, 9) if random.random() < 0.8 else random.randint(10, 13)
            left, right, top = max(0, x), min(64, x + width), h - height
            if right > left:
                bitmaptools.fill_region(city, left, top, right, h, WALL)
                bitmaptools.fill_region(city, left, top, right, top + 1, RIM)
                if height >= 10:  # a mast on the tall ones
                    city[(left + right) // 2, top - 1] = RIM
                for wy in range(top + 2, h - 1, 2):
                    for wx in range(left + 1, right - 1, 2):
                        if random.random() < 0.18:
                            city[wx, wy] = WINDOW if random.random() < 0.75 else WINDOW2
            x += width

    def light_city(self):
        """Walls and roof edges in the light of the last burst."""
        light, color = self.light, self.light_color
        # mixed into the house colour, so lit houses get brighter, never darker
        self.city_pal[WALL] = gfx.mix(WALL_COLOR, gfx.mix(WALL_COLOR, color, 0.13), light)
        self.city_pal[RIM] = gfx.mix(RIM_COLOR, gfx.mix(RIM_COLOR, color, 0.55), light)

    def launch(self):
        shell = random.choice(SHELLS)
        # silver is kept for crackling and flashes: a whole silver shell is a white blob
        family = GOLD if shell == "willow" else random.randrange(SILVER)
        # rising like this, it bursts about 16 to 27 pixels above the bottom
        speed = random.uniform(17.0, 22.0)
        self.rockets.append([random.uniform(8, 56), 31.0, random.uniform(-2.5, 2.5), -speed, shell, family])

    def burst(self, x, y, shell, family):
        sparks = self.sparks
        color = 1 + family * LEVELS
        if shell == "ring":
            count = random.randint(22, 28)
            tilt = random.uniform(0.3, 1.0)  # a ring seen at an angle is an ellipse
            turn = random.uniform(0, math.pi)
            speed = random.uniform(19.0, 24.0)
            for i in range(count):
                a = i * 2 * math.pi / count
                rx, ry = math.cos(a) * speed, math.sin(a) * speed * tilt
                vx = rx * math.cos(turn) - ry * math.sin(turn)
                vy = rx * math.sin(turn) + ry * math.cos(turn)
                life = random.uniform(1.6, 2.0)
                sparks.append([x, y, vx, vy, life, life, color, STAR, [(int(x), int(y))]])
        else:
            kind = {"peony": STAR, "double": STAR, "crackle": CRACKLE, "willow": WILLOW}[shell]
            speed = {"peony": 26.0, "double": 26.0, "crackle": 21.0, "willow": 25.0}[shell]
            inner = 1 + random.randrange(SILVER) * LEVELS
            for i in range(42 if shell in ("double", "crackle") else 36):
                # directions on a sphere, seen from the side: denser at the rim, like a real shell
                z = random.uniform(-1.0, 1.0)
                a = random.uniform(0, 2 * math.pi)
                r = math.sqrt(1.0 - z * z) * speed * random.uniform(0.85, 1.0)
                c = color
                if shell == "double" and i & 1:
                    r *= 0.5  # a smaller inner shell in a second colour
                    c = inner
                life = random.uniform(3.4, 4.2) if kind == WILLOW else random.uniform(1.7, 2.4)
                sparks.append([x, y, math.cos(a) * r, math.sin(a) * r, life, life, c, kind, [(int(x), int(y))]])
        # the flash of the burst: a short-lived bright spark in the middle
        sparks.append([x, y, 0.0, 0.0, 0.15, 0.15, 1 + SILVER * LEVELS, EMBER, [(int(x), int(y))]])
        self.light = 1.0
        self.light_color = FAMILIES[family][1]

    def frame(self, dt):
        # rockets: one every few seconds, sometimes a quick series
        self.wait -= dt
        if self.wait <= 0.0 and len(self.sparks) < MAX_SPARKS:
            self.launch()
            if self.salvo > 0:
                self.salvo -= 1
                self.wait = random.uniform(0.3, 0.7)
            else:
                self.wait = random.uniform(1.0, 3.0)
                if random.random() < 0.08:
                    self.salvo = 2

        bitmap = self.bitmap
        bitmap.fill(0)
        top = LEVELS - 1
        gold = 1 + GOLD * LEVELS
        for rocket in self.rockets[:]:
            rocket[3] += GRAVITY * dt
            x = rocket[0] = rocket[0] + rocket[2] * dt
            y = rocket[1] = rocket[1] + rocket[3] * dt
            if rocket[3] > -3.0:  # almost at the top
                self.rockets.remove(rocket)
                self.burst(x, y, rocket[4], rocket[5])
                continue
            # the rocket sprays short-lived sparks behind it
            life = random.uniform(0.2, 0.45)
            self.sparks.append([x, y, random.uniform(-3, 3), random.uniform(1, 6), life, life, gold, EMBER,
                                [(int(x), int(y))]])
            if 0 <= x < 64 and 0 <= y < 32:
                bitmap[int(x), int(y)] = gold + top

        drags = [math.exp(-drag * dt) for drag in DRAG]
        falls = [GRAVITY * share * dt for share in FALL]
        silver = 1 + SILVER * LEVELS
        alive = []
        for spark in self.sparks:
            x, y, vx, vy, left, life, color, kind, trail = spark
            left -= dt
            drag = drags[kind]
            vx *= drag
            vy = vy * drag + falls[kind]
            x += vx * dt
            y += vy * dt
            if left <= 0.0 or y >= 32.0 or x < 0.0 or x >= 64.0:
                continue
            spark[0], spark[1], spark[2], spark[3], spark[4] = x, y, vx, vy, left
            alive.append(spark)
            ix, iy = int(x), int(y)
            level = int(top * (left / life) ** 0.6 + 0.5)
            if kind == CRACKLE and left < life * 0.6:
                # crackling: the sparks turn into flickering silver points around their path
                if random.random() < 0.5:
                    cx, cy = ix + random.randint(-1, 1), iy + random.randint(-1, 1)
                    if 0 <= cx < 64 and 0 <= cy < 32:
                        bitmap[cx, cy] = silver + random.randint(3, top)
                continue
            if kind == WILLOW:
                level -= random.randint(0, 1)  # gold glitters a little
            # the trail remembers the last pixels, not the last frames
            dims = TRAIL_DIMS[kind]
            if trail[-1] != (ix, iy):
                trail.append((ix, iy))
                if len(trail) > len(dims):
                    trail.pop(0)
            # oldest and dimmest first, the spark itself is drawn last
            for (tx, ty), dim in zip(trail, dims[len(dims) - len(trail):]):
                if level > dim and ty >= 0:
                    bitmap[tx, ty] = color + level - dim
        self.sparks = alive

        # the light of the burst on the city fades
        if self.light > 0.0:
            self.light = max(0.0, self.light - dt * 0.8)
            self.light_city()
