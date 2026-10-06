"""Rentiere: three reindeer gallop through a snowy night, Rudolph in front with his glowing nose.

The landscape scrolls past in three layers at different speeds (mountains, hills with firs, the
snow underfoot), so the herd seems to run while it stays on screen. Each layer is a bitmap whose
right half continues its left half; a TileGrid shows it three times in a row and only moves.
The gallop is six frames in one sprite sheet. Every half minute or so the herd takes off, flies
a while over the hills with a trail of gold dust, and lands again.
"""
import math
import random

import displayio
import vectorio

from app import gfx

FPS = 25
PREVIEW_AT = 3.0
GROUND = 30  # where the hooves touch the snow
SPEED = 24.0  # pixels per second of the snow underfoot; hills and mountains move slower
BOB = (0, -1, -1, 0, 0, 1)  # how far the body is raised in each gallop frame

DEER = (
    (
        "...................",
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBB......",
        "....DL....D.L......",
        ".....DL...DL.......",
        ".....DL..DL........",
        "......DL.DL........",
        "......hhhh.........",
    ),
    (
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBB......",
        "...DL.......DLLL...",
        "...DL........D..h..",
        "...DL.........D....",
        "..DL..........h....",
        "..DL...............",
        ".hh................",
    ),
    (
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBBL.....",
        "..DL........DDLLLLh",
        ".D.L..........D....",
        "D.L............Dh..",
        "h.L................",
        ".h.................",
        "...................",
    ),
    (
        "...................",
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBB......",
        "..D.L......DL......",
        "..DL........DL.....",
        "..DL........DL.....",
        "...hLh......D.L....",
        ".............hh....",
    ),
    (
        "...................",
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBB......",
        "...DL......DL......",
        "....DL.....DL......",
        "....DL.....DL......",
        ".....Dhh..D.L......",
        "..........hh.......",
    ),
    (
        "...................",
        "...................",
        "........a..a.a.....",
        ".........aa.aa.a...",
        "..........aaaaa....",
        "............aa.....",
        "............BBB....",
        "...........BBBeBB..",
        "..........BBBBBBBBN",
        ".ww......BBBBcr....",
        ".wBBBBBBBBBBBBrg...",
        ".BBBBBBBBBBBBBB....",
        ".BBBBBBBBBBBBB.....",
        "..BBBccccccBB......",
        "....DL....D.L......",
        ".....DL...DL.......",
        ".....DL..hL........",
        ".....hh...h........",
    ),
)
DEER_KEYS = {".": 0, "B": 1, "L": 2, "D": 3, "c": 4, "a": 5, "e": 6, "N": 7, "w": 8, "h": 9, "r": 10, "g": 11}
COAT = (0, 0x9A6238, 0xA86C40, 0x6A4020, 0xE8D0A8, 0xD8B080, 0x101010, 0x2A1A10, 0xF4ECE4, 0x6A4020,
        0xD82030, 0xFFD040)
NOSE = 7
GLOW = (
    "..g..",
    ".gGg.",
    "gG.Gg",
    ".gGg.",
    "..g..",
)
MOON = (
    "..mmm..",
    ".mmMM..",
    "mmM....",
    "mmM....",
    "mmM....",
    ".mmMM..",
    "..mmm..",
)
# landscape palette: sky and stars, mountains, hills, firs, snow underfoot
(SKY, STAR1, STAR2, STAR3, MOON_LIGHT, MOON_DARK, PEAK, ROCK, ROCK_DARK, HILL_TOP, HILL, FIR, FIR_DARK,
 FIR_SNOW, TRUNK, CREST, SNOW, SNOW_DARK) = range(18)
LAND = (0x000000, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFF4C0, 0xC8B880, 0x6A78A8, 0x262C4C, 0x1C2038, 0x8090BC,
        0x4C5880, 0x2A6A4C, 0x163E30, 0xC8D8F4, 0x3A2414, 0xD8E2F8, 0x8C9CC4, 0x6878A0)
FIR_ART = (
    "...s...",
    "..sfd..",
    "..sfd..",
    ".sffdd.",
    "..sfd..",
    ".sffdd.",
    "sfffddd",
    "...t...",
)


def periodic(x, waves):
    """Height made of sine waves that repeat every 128 pixels: waves = ((count, size, shift), ...)."""
    return sum(size * math.sin(2 * math.pi * count * x / 128 + shift) for count, size, shift in waves)


class Scene:
    def __init__(self, group, settings):
        self.sky_pal = gfx.Pal(LAND)  # the sky is opaque, the landscape strips in front are not
        self.land_pal = gfx.Pal(LAND, transparent=(0,))
        sky = displayio.Bitmap(64, 32, len(LAND))
        for _ in range(28):
            sky[random.randrange(64), random.randrange(20)] = random.choice((STAR1, STAR2, STAR3))
        gfx.draw_art(sky, MOON, {".": 0, "m": MOON_LIGHT, "M": MOON_DARK}, 50, 2)
        group.append(displayio.TileGrid(sky, pixel_shader=self.sky_pal.palette))
        self.layers = [
            (self.mountains(group), SPEED * 0.12),
            (self.hills(group), SPEED * 0.4),
            (self.snowfield(group), SPEED),
        ]
        self.offsets = [0.0, 0.0, 0.0]

        sheet, w, h = gfx.sprite_sheet(DEER, DEER_KEYS)
        self.rudolph_pal = gfx.Pal(COAT, transparent=(0,))
        # the two behind run a little further back: higher up and in the shade of the others
        far_pal = gfx.Pal([gfx.scale(c, 0.62) for c in COAT], transparent=(0,))
        mid_pal = gfx.Pal([gfx.scale(c, 0.8) for c in COAT], transparent=(0,))
        glow_sheet = gfx.art_bitmap(GLOW, {".": 0, "g": 1, "G": 2})
        self.glow_pal = gfx.Pal((0, 0x400404, 0x900C0C), transparent=(0,))
        self.glow = displayio.TileGrid(glow_sheet, pixel_shader=self.glow_pal.palette)
        group.append(self.glow)
        self.deer = []
        for i, (home, back, pal) in enumerate(((2, 4, far_pal), (22, 2, mid_pal), (43, 0, self.rudolph_pal))):
            grid = displayio.TileGrid(sheet, pixel_shader=pal.palette, tile_width=w, tile_height=h)
            group.append(grid)
            # grid, home x, rows further back, gallop phase, wander phase, delay when taking off
            self.deer.append([grid, home, back, random.random() * 6, random.uniform(0, 6.3), 0.5 * (2 - i)])
        self.rudolph = self.deer[2][0]

        self.dust_pal = gfx.Pal((0, 0xFFF0A0, 0xFFC040, 0xC07010, 0x603008), transparent=(0,))
        self.dust = []
        for _ in range(14):
            dot = vectorio.Rectangle(pixel_shader=self.dust_pal.palette, width=1, height=1, x=0, y=0, color_index=1)
            dot.hidden = True
            group.append(dot)
            self.dust.append([dot, 0.0, 0.0, 9.0])  # shape, x, y, age
        self.next_dust = 0.0
        self.flake_pal = gfx.Pal((0xFFFFFF, 0xA0AECC))
        self.flakes = []
        for i in range(18):
            rect = vectorio.Rectangle(pixel_shader=self.flake_pal.palette, width=1, height=1, x=0, y=0,
                                      color_index=i % 2)
            group.append(rect)
            self.flakes.append([rect, random.uniform(0, 64), random.uniform(0, 32), random.uniform(3.0, 6.0)])

        self.t = 0.0
        self.flight = 0.0  # seconds into the current flight, or 0 while running
        self.next_flight = random.uniform(18, 30)
        self.flight_length = 12.0

    def strip(self, group, rows, top):
        """A landscape layer: bitmap 128 wide that repeats, shown three times by one TileGrid."""
        bitmap = displayio.Bitmap(128, rows, len(LAND))
        grid = displayio.TileGrid(bitmap, pixel_shader=self.land_pal.palette, width=3, height=1,
                                  tile_width=64, tile_height=rows, y=top)
        grid[0], grid[1], grid[2] = 0, 1, 0
        group.append(grid)
        return bitmap, grid

    def mountains(self, group):
        bitmap, grid = self.strip(group, 12, 13)
        for x in range(128):
            top = int(6.0 + periodic(x, ((2, 2.5, 0.3), (5, 1.6, 1.1), (11, 0.7, 2.0))))
            for y in range(max(0, top), 12):
                if y - top < 2 and top < 6:
                    bitmap[x, y] = PEAK  # snow on the higher peaks
                else:
                    bitmap[x, y] = ROCK if (x + y) % 7 else ROCK_DARK
        return grid

    def hills(self, group):
        bitmap, grid = self.strip(group, 12, 18)
        tops = [int(7.0 + periodic(x, ((3, 1.6, 0.0), (7, 0.8, 1.3)))) for x in range(128)]
        for x in range(128):
            for y in range(tops[x], 12):
                bitmap[x, y] = HILL_TOP if y == tops[x] else HILL
        for x in (6, 23, 31, 52, 70, 88, 97, 115):
            gfx.draw_art(bitmap, FIR_ART, {".": 0, "s": FIR_SNOW, "f": FIR, "d": FIR_DARK, "t": TRUNK},
                         x - 3, tops[x] - len(FIR_ART) + 2)
        return grid

    def snowfield(self, group):
        bitmap, grid = self.strip(group, 4, 28)
        for x in range(128):
            for y in range(4):
                bitmap[x, y] = CREST if y == 0 else SNOW
            if (x * 37) % 23 < 3:
                bitmap[x, 1 + (x * 7) % 3] = SNOW_DARK  # bumps and tracks, so the motion shows
        return grid

    def frame(self, dt):
        self.t += dt
        t = self.t
        # the world scrolls left; each layer wraps after one period of 128 pixels
        for i, (grid, speed) in enumerate(self.layers):
            self.offsets[i] = (self.offsets[i] + speed * dt) % 128
            grid.x = -int(self.offsets[i])

        self.fly(dt)
        for i, deer in enumerate(self.deer):
            grid, home, back, phase, wander, delay = deer
            rise = self.rise(delay)
            # gallop: twelve frames a second on the ground, slower strokes in the air
            deer[3] = (phase + dt * (12.5 - 4.5 * rise)) % 6
            grid[0] = int(deer[3])
            grid.x = int(home + 2.5 * math.sin(t * 0.23 + wander))
            y = GROUND - 17 - back - rise * (10 - back + 2.0 * math.sin(t * 1.7 + i))
            grid.y = int(y)
            if rise > 0.2:
                self.trail(dt, grid.x + 2, grid.y + 15)
        # Rudolph's nose glows, and so does the air round it
        pulse = 0.5 + 0.5 * math.sin(t * 4.0)
        self.rudolph_pal[NOSE] = gfx.mix(0xB01010, 0xFF4040, pulse)
        self.glow_pal[1] = gfx.scale(0x400404, 0.5 + 0.5 * pulse)
        self.glow_pal[2] = gfx.scale(0x900C0C, 0.6 + 0.4 * pulse)
        self.glow.x = self.rudolph.x + 16
        self.glow.y = self.rudolph.y + 6 + BOB[self.rudolph[0]]
        for i in range(3):
            self.sky_pal[STAR1 + i] = gfx.scale(0xE8F0FF, 0.6 + 0.4 * math.sin(t * (0.9 + 0.3 * i) + 2.0 * i))
        self.move_dust(dt)
        self.snow(dt)

    def fly(self, dt):
        """Flight timetable: now and then a flight of 9 to 14 seconds."""
        if self.flight == 0.0:
            self.next_flight -= dt
            if self.next_flight <= 0:
                self.flight = 0.001
                self.flight_length = random.uniform(9, 14)
        else:
            self.flight += dt
            if self.flight > self.flight_length + 4:
                self.flight = 0.0
                self.next_flight = random.uniform(25, 45)

    def rise(self, delay):
        """0 on the ground, 1 high in the air; delay: how much later than Rudolph a deer follows."""
        f = self.flight
        if f == 0.0:
            return 0.0
        # up over 2.5 seconds and down again at the end, gently at both ends
        up = min(1.0, max(0.0, (f - delay) / 2.5))
        down = min(1.0, max(0.0, (self.flight_length - f + delay) / 2.5))
        v = min(up, down)
        return v * v * (3 - 2 * v)

    def trail(self, dt, x, y):
        self.next_dust -= dt
        if self.next_dust > 0:
            return
        self.next_dust = 0.05
        for dot in self.dust:
            if dot[3] > 1.2:
                dot[1], dot[2], dot[3] = float(x + random.randrange(4)), float(y + random.randrange(3)), 0.0
                dot[0].hidden = False
                return

    def move_dust(self, dt):
        for dot in self.dust:
            if dot[3] > 1.2:
                continue
            dot[3] += dt
            dot[1] -= SPEED * 0.6 * dt
            dot[2] += 3.0 * dt
            if dot[3] > 1.2:
                dot[0].hidden = True
                continue
            dot[0].x = int(dot[1])
            dot[0].y = int(dot[2])
            dot[0].color_index = 1 + min(3, int(dot[3] * 3.3))

    def snow(self, dt):
        # the herd runs right, so the flakes seem to blow past to the left
        for f in self.flakes:
            f[2] += f[3] * dt
            f[1] -= 7.0 * dt
            if f[2] >= 32 or f[1] < -1:
                f[1] = random.uniform(0, 70)
                f[2] = -1.0
            f[0].x = int(f[1])
            f[0].y = int(f[2])
