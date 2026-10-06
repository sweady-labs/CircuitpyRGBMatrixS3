"""Adventskranz: a fir wreath with berries, ribbons and a bow, four red candles with flickering flames.

In Advent as many candles burn as Advent Sundays have passed (the 1st Advent is the fourth
Sunday before Christmas), and a candle that has burned for weeks is lower than the newer ones.
Before Advent, after Christmas and while the clock is not set, all four burn, so the wreath
always looks festive.

Wreath and candles are one bitmap, drawn once, back to front. Every frame only the flame sprites
change, and a few palette colors: the candle tops and the needles near each flame glow with it.
"""
import math
import random

import displayio

from app import clock, gfx

FPS = 25
PREVIEW_AT = 3.0

CX, CY, RX, RY = 32, 24, 23, 4  # centre line of the wreath, an ellipse: seen from a little above
TUBE_X, TUBE_Y = 4.6, 3.1  # half size of the wreath's cross section on the screen
ANGLES = (110, 200, 290, 20)  # candles round the wreath, in the order they are lit (90 = front)
FULL = 9  # height of a fresh candle
STEP = 3  # angle step of the needle tufts round the wreath

# palette of the one big bitmap
NEEDLE = 1  # 3 shades for each of 9 light zones: 0 unlit, then near and further for each candle
BERRY = NEEDLE + 3 * 9  # red, dark red, shine
RIBBON = BERRY + 3  # light, mid, dark
GOLD = RIBBON + 3  # two groups that sparkle in turn
CONE = GOLD + 2  # light, dark
WAX = CONE + 2  # light, mid, dark, shadow, rim
WICK = WAX + 5
TOP = WICK + 1  # 2 per candle: glowing wax under the flame, the pool at the wick
COLORS = TOP + 8

NEEDLES = (0x062A14, 0x12602A, 0x3A9C44)  # dark, mid, light
BERRIES = (0xE0182C, 0x800818, 0xFFC0C8)
RIBBONS = (0xF04048, 0xC8102A, 0x700818)
CONES = (0x8A5A2C, 0x4A2C14)
WAXES = (0xFF4050, 0xD01828, 0x8E0C1A, 0x500812, 0xFF6878)
WARM = 0xFFA040
DECOR = ((3, "gold"), (42, "berries"), (90, "gold"), (135, "berries"), (156, "ribbon"), (177, "cone"),
         (186, "gold"), (228, "berries"), (246, "ribbon"), (267, "gold"), (315, "berries"), (336, "ribbon"),
         (354, "cone"))  # (angle, what), angles are multiples of STEP
BOW = (
    ".rr...rr.",
    "rLrr.rrLr",
    "rLLrkrLLr",
    ".rrrLrrr.",
    "...rkr...",
    "..rr.rr..",
    ".rr...rr.",
)
FLAME = (
    ("..1..", "..1..", ".121.", ".232.", ".343.", ".242.", "..5..", "....."),
    (".1...", "..1..", ".121.", ".232.", ".343.", ".242.", "..5..", "....."),  # leaning left
    ("...1.", "..1..", ".121.", ".232.", ".343.", ".242.", "..5..", "....."),  # leaning right
    (".....", "..1..", ".121.", ".232.", ".343.", ".242.", "..5..", "....."),  # ducking
    ("..1..", "..2..", ".121.", ".232.", ".343.", ".343.", "..5..", "....."),  # stretching
)
FLAME_COLORS = (0, 0xFF6A10, 0xFFB030, 0xFFE68A, 0xFFFFF0, 0x3858E0)


def day_number(year, month, day):
    """Days since a fixed date long ago; the difference of two is the days between them."""
    if month < 3:
        year -= 1
        month += 12
    return 365 * year + year // 4 - year // 100 + year // 400 + (153 * (month - 3) + 2) // 5 + day


def advent_sundays(local):
    """Advent Sundays passed (1-4) from the 1st Advent up to Christmas Eve, otherwise None."""
    if local is None:
        return None
    christmas = day_number(local.tm_year, 12, 25)
    today = day_number(local.tm_year, local.tm_mon, local.tm_mday)
    eve_weekday = (local.tm_wday + christmas - 1 - today) % 7  # tm_wday: Monday 0 ... Sunday 6
    fourth = christmas - 1 - (eve_weekday + 1) % 7  # the Sunday on or before Christmas Eve
    first = fourth - 21
    if first <= today < christmas:
        return min(4, 1 + (today - first) // 7)
    return None


def hash16(n):
    """A fixed pseudo random number 0..65535 for n, so the wreath looks the same every time."""
    n = (n * 40503 + 12345) & 0xFFFF
    return ((n ^ (n >> 7)) * 2753) & 0xFFFF


def ring(angle):
    a = math.radians(angle)
    return CX + RX * math.cos(a), CY + RY * math.sin(a)


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * COLORS)
        pal = self.pal
        for zone in range(9):
            for shade in range(3):
                pal[NEEDLE + 3 * zone + shade] = NEEDLES[shade]
        for first, colors in ((BERRY, BERRIES), (RIBBON, RIBBONS), (CONE, CONES), (WAX, WAXES)):
            for i, color in enumerate(colors):
                pal[first + i] = color
        pal[WICK] = 0x3A2A24
        sheet, w, h = gfx.sprite_sheet(FLAME, {".": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5})
        self.flame_pal = gfx.Pal(FLAME_COLORS, transparent=(0,))
        self.flames = []
        for _ in ANGLES:
            grid = displayio.TileGrid(sheet, pixel_shader=self.flame_pal.palette, tile_width=w, tile_height=h)
            group.append(grid)
            self.flames.append(grid)
        self.flicker = [1.0] * 4
        self.target = [1.0] * 4
        self.draft = 0.0  # a draught leans all flames the same way for a moment
        self.draft_time = random.uniform(6, 15)
        self.twinkle = 0.0
        self.lit = 0
        self.sundays = -1  # not a possible value, so the first check draws
        self.check = 60.0  # seconds until the date is checked again
        self.check_date()

    # --- drawing: once, and again when the number of candles changes ---------------------------

    def draw(self, sundays):
        """sundays: Advent Sundays passed, or None outside Advent (all four burn, all fresh)."""
        lit = sundays or 4
        self.lit = lit
        self.bitmap.fill(0)
        self.tops = []
        for k, angle in enumerate(ANGLES):
            x, y = ring(angle)
            # in Advent a candle is a pixel lower for every week it burned before this one
            burned = sundays - 1 - k if sundays and k < sundays else 0
            self.tops.append((int(x + 0.5), int(y - 2) - (FULL - burned)))
        self.zones = bytearray(b"\xff" * (64 * 32))  # light zone of each pixel, worked out when needed
        # back half of the wreath, the candles standing on it, then the front half
        self.wreath(180, 360)
        for k, angle in enumerate(ANGLES):
            if math.sin(math.radians(angle)) < 0:
                self.candle(k, k < lit)
        self.wreath(0, 181)
        x, y = ring(66)
        keys = {".": 0, "r": RIBBON + 1, "L": RIBBON, "k": RIBBON + 2}
        gfx.draw_art(self.bitmap, BOW, keys, int(x) - 4, int(y) - 3)
        for k, angle in enumerate(ANGLES):
            if math.sin(math.radians(angle)) >= 0:
                self.candle(k, k < lit)
        for k, grid in enumerate(self.flames):
            x, top = self.tops[k]
            grid.x = x - 2
            grid.y = top - 8
            grid.hidden = k >= lit

    def wreath(self, first, last):
        """Fir needles bristling out of the ring from angle first to last, back to front, then
        the berries, ribbons and cones of that part on top."""
        b = self.bitmap
        for angle in sorted(range(first, last, STEP), key=lambda a: math.sin(math.radians(a))):
            x0, y0 = ring(angle)
            for i in range(9):
                h = hash16(angle * 16 + i)
                # a needle pointing out from the middle of the wreath, round its cross section
                phi = (i + (h & 7) / 8) / 9 * 2 * math.pi
                c, s = math.cos(phi), math.sin(phi)
                length = 0.65 + (h >> 4 & 7) / 16
                x1 = x0 + c * TUBE_X * length
                y1 = y0 + s * TUBE_Y * length
                # lit from above: needles pointing up are light, the underside is dark
                body = 1 if s < 0.3 else 0
                tip = 2 if s < -0.2 else 1 if s < 0.5 else 0
                steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for k in range(steps + 1):
                    px = int(x0 + (x1 - x0) * k / steps)
                    py = int(y0 + (y1 - y0) * k / steps)
                    if 0 <= px < 64 and 0 <= py < 32:
                        b[px, py] = NEEDLE + 3 * self.zone(px, py) + (tip if k == steps else body)
        # decorations last, so the needles of this half do not cover them
        for angle, kind in DECOR:
            if first <= angle < last:
                x0, y0 = ring(angle)
                self.decorate(kind, int(x0), int(y0))

    def zone(self, px, py):
        """Which flame lights this needle: 0 none, 1 + 2k near flame k, 2 + 2k a little further."""
        zone = self.zones[py * 64 + px]
        if zone == 255:
            best, zone = 14.0, 0
            for k in range(self.lit):
                x, top = self.tops[k]
                d = math.sqrt((px - x) ** 2 + ((py - top + 4) * 1.4) ** 2)
                if d < best:
                    best = d
                    zone = 1 + 2 * k if d < 9 else 2 + 2 * k
            self.zones[py * 64 + px] = zone
        return zone

    def decorate(self, kind, x, y0):
        b = self.bitmap
        y = y0 - 1
        if not (2 <= x < 62 and 3 <= y < 30):
            return
        if kind == "berries":
            # a cluster of berries, one with a shine
            for dx, dy, c in ((0, 0, 0), (1, 0, 1), (-1, 0, 0), (0, -1, 2), (1, -1, 0), (0, 1, 1), (-1, -1, 0)):
                b[x + dx, y + dy] = BERRY + c
        elif kind == "gold":
            # a little gold bauble; its pixels belong to both sparkle groups
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                b[x + dx, y + dy] = GOLD + (dx + dy + x) % 2
        elif kind == "ribbon":
            # red velvet wound round the wreath: a slanted band across it
            for dy in range(-3, 4):
                if 0 <= y0 + dy < 32:
                    xx = x - dy // 2
                    b[xx, y0 + dy] = RIBBON + (0 if dy < -1 else 1)
                    b[xx + 1, y0 + dy] = RIBBON + (1 if dy < 1 else 2)
        elif kind == "cone":
            for dx, dy, c in ((0, -1, 0), (1, -1, 1), (0, 0, 1), (1, 0, 0), (0, 1, 0), (1, 1, 1), (0, 2, 1)):
                b[x + dx, y + dy] = CONE + c

    def candle(self, k, lit):
        b = self.bitmap
        x, top = self.tops[k]
        base = int(ring(ANGLES[k])[1] - 1)
        shades = (WAX + 1, WAX, WAX + 1, WAX + 2, WAX + 3)  # left to right, lit from the left
        for py in range(top, min(32, base + 1)):
            for i in range(5):
                b[x - 2 + i, py] = shades[i]
        if lit:
            # the wax glows under the flame, a drip runs down the side
            for px in range(x - 2, x + 3):
                b[px, top + 1] = TOP + 2 * k
            for px in range(x - 1, x + 2):
                b[px, top] = TOP + 2 * k + 1
            b[x + 1, top + 2] = WAX + 4
            b[x + 1, top + 3] = WAX + 4
        else:
            for px in range(x - 1, x + 2):
                b[px, top] = WAX + 4
        b[x, top - 1] = WICK

    # --- animation ---------------------------------------------------------------------------

    def check_date(self):
        sundays = advent_sundays(clock.now())
        if sundays != self.sundays:
            self.sundays = sundays
            self.draw(sundays)

    def frame(self, dt):
        self.check -= dt
        if self.check <= 0:
            self.check = 60.0  # the date changes slowly
            self.check_date()

        self.draft_time -= dt
        if self.draft_time <= 0:
            self.draft_time = random.uniform(8, 20)
            self.draft = random.choice((-1.0, 1.0))
        self.draft *= 1.0 - min(1.0, dt * 0.8)

        pal = self.pal
        for k in range(self.lit):
            # brightness wanders towards a new random target now and then
            if random.random() < dt * 6:
                self.target[k] = random.uniform(0.75, 1.0)
            self.flicker[k] += (self.target[k] - self.flicker[k]) * min(1.0, dt * 12)
            f = self.flicker[k]
            grid = self.flames[k]
            if abs(self.draft) > 0.35:
                grid[0] = 1 if self.draft < 0 else 2
            elif random.random() < dt * 5:
                grid[0] = random.choice((0, 0, 0, 3, 4, 1, 2))
            pal[TOP + 2 * k] = gfx.mix(0xD01828, 0xFF8848, 0.55 * f)
            pal[TOP + 2 * k + 1] = gfx.mix(0xFF6040, 0xFFD080, f - 0.2)
            for shade in range(3):
                needle = NEEDLES[shade]
                pal[NEEDLE + 3 * (1 + 2 * k) + shade] = gfx.mix(needle, WARM, 0.3 * f)
                pal[NEEDLE + 3 * (2 + 2 * k) + shade] = gfx.mix(needle, WARM, 0.13 * f)
        self.flame_pal[3] = gfx.mix(0xFFD060, 0xFFF0B0, self.flicker[0])

        self.twinkle += dt
        sparkle = 0.5 + 0.5 * math.sin(self.twinkle * 1.7)
        pal[GOLD] = gfx.mix(0x8A6010, 0xFFE070, sparkle)
        pal[GOLD + 1] = gfx.mix(0x8A6010, 0xFFE070, 1.0 - sparkle)
