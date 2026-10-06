"""Weihnachtsgeschichte: a little Christmas story in five chapters, over and over again.

1. A snowy night: stars, the moon, a village on the hills.
2. Father Christmas's sleigh flies across the sky, Rudolph in front.
3. The view moves along to a cosy house; the sleigh lands in front of it and flies off again.
4. Inside: the tree glows, the fire crackles, and presents appear one by one.
5. A big star and "Frohe Weihnachten", shooting stars as in the first night.

Chapters 1-3 share one landscape that is wider than the screen: the view moves by moving its
layers. Between the other chapters the picture fades out and in: all palettes of the story are
dimmed together (scaled colors), the pixels themselves stay as they are.
"""
import math
import random

import displayio
import vectorio

from app import gfx

FPS = 20
PREVIEW_AT = 5.0
FADE = 1.2  # seconds to fade out or in
# (chapter, seconds, fades in, fades out)
CHAPTERS = (("night", 12.0, True, False), ("sleigh", 10.0, False, False), ("house", 17.0, False, True),
            ("presents", 17.0, True, True), ("finale", 15.0, True, True))
HOUSE_X = 90  # where the house stands in the landscape
PAN = 62  # how far the view moves to see the house

# --- pixel art ---------------------------------------------------------------------------------

MOON = (
    "..mmm..",
    ".mmMM..",
    "mmM....",
    "mmM....",
    "mmM....",
    ".mmMM..",
    "..mmm..",
)
FIR = (
    "...s...",
    "..sfd..",
    "..sfd..",
    ".sffdd.",
    "..sfd..",
    ".sffdd.",
    "sfffddd",
    "...t...",
)
HOUSE = (
    "...................kk...",
    "...........S.......kk...",
    "..........SsS......kk...",
    ".........SsssS.....kk...",
    "........SsssssS....kk...",
    ".......SsssssssS...kk...",
    "......SsssssssssS..kk...",
    ".....SsssssssssssS.kk...",
    "....SsssssssssssssSS....",
    "...SsssssssssssssssssS..",
    "..oooooooooooooooooooooo",
    "...RiRRRiRRRRRRiRRRRiR..",
    "...RRRRRRRRRRRRRRRRRRR..",
    "...ReeeeeeeeeeRRRdddDRR.",
    "...RewwwwywwweRRRdgdDRR.",
    "...RewwwwgwwweRRRgpgDRR.",
    "...RewwwgggwweRRRdgdDRR.",
    "...RewwgggggweRRRdddDRR.",
    "...ReeeeeeeeeeRRRdddDRR.",
    "...RRRRRRRRRRRRRRdddDRR.",
)
SNOWMAN = (
    "..kkk..",
    ".kkkkk.",
    "..sss..",
    "..sso..",
    ".sssss.",
    "sssssss",
    ".sssss.",
)
VILLAGE_HOUSE = (
    ".r.",
    "rrr",
    "bwb",
)
CHURCH = (
    "..y..",
    "..r..",
    ".rrr.",
    ".bwb.",
    "rrrrr",
    "bwbwb",
)
SLEIGH = (
    (
        ".....RRx..................",
        "....RRRR..............a.a.",
        "....fxxR...............a..",
        "...cxxxRR.....a.a.....BBN.",
        "..cccRRRRyy....a.yy.BBBB..",
        ".RRRRRRRRR.yyy.BBn.BBBBB..",
        "..RRRRRRRR...BBBB..B...B..",
        "..YYYYYYYYYY.B..B.........",
        "...........Y..............",
    ),
    (
        ".....RRx..................",
        "....RRRR..............a.a.",
        "....fxxR...............a..",
        "...cxxxRR.....a.a.....BBN.",
        "..cccRRRRyy....a.yy.BBBB..",
        ".RRRRRRRRR.yyy.BBn.BBBBB..",
        "..RRRRRRRR...BBBB...B.B...",
        "..YYYYYYYYYY..BB..........",
        "...........Y..............",
    ),
)
SLEIGH_KEYS = {".": 0, "R": 1, "x": 2, "f": 3, "c": 4, "y": 5, "Y": 6, "a": 7, "B": 8, "N": 9, "n": 10}
SLEIGH_COLORS = (0, 0xC82830, 0xFFFFFF, 0xF0C8A0, 0x8A5A30, 0xFFD040, 0xC89020, 0xD8B080, 0x9A6238,
                 0xFF2020, 0x2A1A10)

# landscape palette (sky, far hills and the near landscape share it)
(CLEAR, STAR1, STAR2, STAR3, MOON_LIGHT, MOON_DARK, FAR, FAR_TOP, ROOF_RED, WALL_DARK, VILLAGE_WINDOW,
 STEEPLE, GROUND, GROUND_TOP, GROUND_DARK, FIR_LIT, FIR_DARK, FIR_SNOW, TRUNK, ROOF_SNOW, ROOF_EDGE,
 STONE, EAVES, ICICLE, WALL, FRAME, WINDOW, TREE, TREE_STAR, DOOR, DOOR_DARK, WREATH, CARROT) = range(33)
LAND = (0, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFF4C0, 0xC8B880, 0x2A3254, 0x4A5680, 0x8A2028, 0x3A2014,
        0xFFC860, 0xFFD040, 0x8292BA, 0xD8E2F8, 0x6878A0, 0x2A6A4C, 0x163E30, 0xC8D8F4, 0x3A2414,
        0xB8C6E4, 0xE8F0FF, 0x707080, 0x5A6A94, 0xC8DCF8, 0xB82830, 0xF0F0F0, 0xFFC860, 0x1E7A3A,
        0xFFD040, 0x2E6A3A, 0x1C4024, 0xE02030, 0xFF8020)
HOUSE_KEYS = {".": 0, "k": STONE, "S": ROOF_EDGE, "s": ROOF_SNOW, "o": EAVES, "i": ICICLE, "R": WALL,
              "e": FRAME, "w": WINDOW, "g": TREE, "y": TREE_STAR, "d": DOOR, "D": DOOR_DARK, "p": WREATH}
FIR_KEYS = {".": 0, "s": FIR_SNOW, "f": FIR_LIT, "d": FIR_DARK, "t": TRUNK}

# the room of chapter 4
(R_CLEAR, BRICK, BRICK_DARK, MORTAR, MANTEL, MANTEL_DARK, FLOOR, FLOOR_DARK, FLOOR_TOP, SOOT, LOG_WOOD,
 STOCKING_RED, STOCKING_GREEN, STOCKING_WHITE, PANE, SASH, PANE_SNOW, NEEDLE_LIT, NEEDLE, NEEDLE_DARK, GARLAND,
 BALL_RED, BALL_BLUE, BALL_GOLD, LIGHT1, LIGHT2, LIGHT3, STAR, STAR_GLOW, POT, POT_DARK) = range(31)
ROOM = (0, 0xB84834, 0x8E3020, 0x4A3A38, 0x7A4A26, 0x4A2A12, 0x5A3418, 0x38200E, 0x8A5A30, 0x100808,
        0x5A3418, 0xD02030, 0x20A040, 0xF0F0F0, 0x0C1A40, 0x6A4022, 0xC8D8F8, 0x2E8A44, 0x1C6A30, 0x0E4220,
        0xE0B040, 0xE01830, 0x3070F0, 0xFFC830, 0xFFF0C0, 0xFFD040, 0xFF6080, 0xFFE060, 0xA07818, 0xB02828,
        0x701418)
FIRE_COLORS = (0, 0xA01808, 0xF04810, 0xFFA020, 0xFFE070)  # embers, red, orange, yellow
STOCKING = (
    "www..",
    "rrr..",
    "rrr..",
    "rrrr.",
    "rrrrr",
    ".rrr.",
)
FIRE = (
    (".....2.....", "..2..3..2..", "..3.343.32.", ".3433443432", "34444444443", "13333333331"),
    ("...2.......", "..32...2...", ".343..23.2.", ".3443343432", "34444444443", "13333333331"),
    (".......2...", "..2...32...", ".23.2.343.2", "2343343443.", "34444444443", "13333333331"),
)
# presents: (x, y on the floor line, width, height, box color, ribbon color)
PRESENTS = ((24, 27, 8, 6, 0xD02030, 0xFFD040), (33, 27, 6, 5, 0x3070F0, 0xF0F0F0),
            (40, 27, 8, 7, 0x20A040, 0xE02030), (50, 27, 7, 5, 0xE0B040, 0xC02030),
            (57, 27, 6, 6, 0xB040D0, 0xFFD040))
# the finale
BIG_STAR = (
    ".....a.....",
    ".....a.....",
    ".....b.....",
    "..c..b..c..",
    "...cbBbc...",
    "aabbBWBbbaa",
    "...cbBbc...",
    "..c..b..c..",
    ".....b.....",
    ".....a.....",
    ".....a.....",
)
BANDS = 16  # color bands across the text, for the glint
GLINT = (
    (".....", ".....", "..a..", ".....", "....."),
    (".....", "..b..", ".bab.", "..b..", "....."),
    ("..b..", "..a..", "baaab", "..a..", "..b.."),
)
STREAK = (
    "a.....",
    ".bb...",
    "...cc.",
    ".....W",
)


def ease(v):
    v = min(1.0, max(0.0, v))
    return v * v * (3 - 2 * v)


class Scene:
    def __init__(self, group, settings):
        self.statics = []  # (palette, colors): everything the fades dim
        self.fade = 1.0
        self.outdoor = displayio.Group()
        group.append(self.outdoor)
        self.landscape()
        self.sleigh_layer()
        self.room = displayio.Group()
        self.room.hidden = True
        group.append(self.room)
        self.build_room()
        self.ending = displayio.Group()
        self.ending.hidden = True
        group.append(self.ending)
        self.build_finale()
        sheet, w, h = gfx.sprite_sheet(GLINT, {".": 0, "a": 1, "b": 2})
        self.glint_pal = self.pal((0, 0xFFFFFF, 0xFFE0A0))
        self.glints = []
        for _ in range(3):
            grid = displayio.TileGrid(sheet, pixel_shader=self.glint_pal.palette, tile_width=w, tile_height=h)
            grid.hidden = True
            group.append(grid)
            self.glints.append([grid, 9.0])  # grid, age (negative: waiting to start)
        self.flakes = []
        self.flake_pal = self.pal((0xFFFFFF, 0x9AA6C0), ())
        for i in range(20):
            rect = vectorio.Rectangle(pixel_shader=self.flake_pal.palette, width=1, height=1, x=0, y=0,
                                      color_index=i % 2)
            group.append(rect)
            self.flakes.append([rect, random.uniform(0, 64), random.uniform(0, 32), random.uniform(2.5, 5.0)])
        self.chapter = -1
        self.time = 0.0
        self.t = 0.0
        self.cam = 0.0
        self.start(0)

    def pal(self, colors, transparent=(0,)):
        pal = gfx.Pal(colors, transparent)
        self.statics.append((pal, list(colors)))
        return pal

    def lit(self, color):
        """A color as it should show now, during a fade dimmed with everything else."""
        return gfx.scale(color, self.fade) if self.fade < 1.0 else color

    # --- the landscape of chapters 1-3 ---------------------------------------------------------

    def landscape(self):
        self.land_pal = self.pal(LAND)
        sky = displayio.Bitmap(64, 32, len(LAND))
        for i in range(30):
            sky[random.randrange(64), random.randrange(18)] = STAR1 + i % 3
        gfx.draw_art(sky, MOON, {".": 0, "m": MOON_LIGHT, "M": MOON_DARK}, 50, 2)
        self.sky = displayio.TileGrid(sky, pixel_shader=self.land_pal.palette)
        self.outdoor.append(self.sky)
        streak = gfx.art_bitmap(STREAK, {".": 0, "a": 1, "b": 2, "c": 3, "W": 4})
        self.streak_pal = self.pal((0, 0x303848, 0x606C88, 0xA0B0D0, 0xFFFFFF))
        self.streak = displayio.TileGrid(streak, pixel_shader=self.streak_pal.palette)
        self.streak.hidden = True
        self.outdoor.append(self.streak)  # a shooting star, behind the hills

        # far hills with a village, half as wide again as the screen (they move at half speed)
        far = displayio.Bitmap(96, 14, len(LAND))
        tops = [int(6.5 + 2.0 * math.sin(x * 0.07 + 0.5) + 1.0 * math.sin(x * 0.19)) for x in range(96)]
        for x in range(96):
            for y in range(tops[x], 14):
                far[x, y] = FAR_TOP if y == tops[x] else FAR
        keys = {".": 0, "r": ROOF_RED, "b": WALL_DARK, "w": VILLAGE_WINDOW, "y": STEEPLE}
        for x in (20, 25, 34, 39, 58, 63):
            gfx.draw_art(far, VILLAGE_HOUSE, keys, x, tops[x + 1] - 1)
        gfx.draw_art(far, CHURCH, keys, 28, tops[30] - 4)
        self.far = displayio.TileGrid(far, pixel_shader=self.land_pal.palette, y=13)
        self.outdoor.append(self.far)

        # near landscape: snowy ground, firs, the house and a snowman
        near = displayio.Bitmap(128, 22, len(LAND))
        self.ground = [int(18.0 - 1.5 * math.sin(x * 0.06) + 0.6 * math.sin(x * 0.23)) for x in range(128)]
        for x in range(HOUSE_X - 4, HOUSE_X + 30):
            self.ground[x] = 19  # flat round the house
        for x in range(128):
            for y in range(self.ground[x], 22):
                near[x, y] = GROUND_TOP if y == self.ground[x] else GROUND_DARK if (x * 3 + y * 5) % 13 == 0 else GROUND
        for x in (3, 15, 46, 57, 79, 122):
            gfx.draw_art(near, FIR, FIR_KEYS, x - 3, self.ground[x] - len(FIR) + 2)
        gfx.draw_art(near, HOUSE, HOUSE_KEYS, HOUSE_X, 0)
        gfx.draw_art(near, SNOWMAN, {".": 0, "k": WALL_DARK, "s": GROUND_TOP, "o": CARROT}, HOUSE_X + 26, 13)
        self.near = displayio.TileGrid(near, pixel_shader=self.land_pal.palette, y=10)
        self.outdoor.append(self.near)

        self.smoke_pal = self.pal((0, 0x7A8098, 0x5C6278, 0x40465C, 0x2A2E40))
        self.puffs = []
        for i in range(4):
            circle = vectorio.Circle(pixel_shader=self.smoke_pal.palette, radius=1, x=0, y=-5, color_index=1)
            self.outdoor.append(circle)
            self.puffs.append([circle, 0.0, 0.0, -0.3 - i * 0.8])  # shape, world x, y, age

    def sleigh_layer(self):
        sheet, w, h = gfx.sprite_sheet(SLEIGH, SLEIGH_KEYS)
        self.sleigh_pal = self.pal(SLEIGH_COLORS)
        self.sleigh = displayio.TileGrid(sheet, pixel_shader=self.sleigh_pal.palette, tile_width=w, tile_height=h)
        self.sleigh.hidden = True
        self.outdoor.append(self.sleigh)
        self.dust_pal = self.pal((0, 0xFFF0A0, 0xFFC040, 0xC07010, 0x603008))
        self.dust = []
        for _ in range(12):
            dot = vectorio.Rectangle(pixel_shader=self.dust_pal.palette, width=1, height=1, x=0, y=0, color_index=1)
            dot.hidden = True
            self.outdoor.append(dot)
            self.dust.append([dot, 0.0, 0.0, 9.0])  # shape, x, y, age
        self.next_dust = 0.0

    # --- chapters ------------------------------------------------------------------------------

    def start(self, chapter):
        self.chapter = chapter
        self.time = 0.0
        name = CHAPTERS[chapter][0]
        # the landscape for the first three chapters, its sky also behind the finale
        outside = name in ("night", "sleigh", "house")
        self.outdoor.hidden = name == "presents"
        self.far.hidden = self.near.hidden = not outside
        self.room.hidden = name != "presents"
        self.ending.hidden = name != "finale"
        for flake in self.flakes:
            flake[0].hidden = name == "presents"
        for puff in self.puffs:
            puff[0].hidden = True
        if name == "night":
            self.cam = 0.0
            self.sleigh.hidden = True
            self.place_camera()
        if name == "presents":
            for present in self.presents:
                present.hidden = True
        if name == "finale":
            self.sleigh.hidden = True

    def frame(self, dt):
        self.t += dt
        self.time += dt
        name, length, fades_in, fades_out = CHAPTERS[self.chapter]
        if self.time >= length:
            self.start((self.chapter + 1) % len(CHAPTERS))
            name, length, fades_in, fades_out = CHAPTERS[self.chapter]
        fade = 1.0
        if fades_in:
            fade = min(fade, self.time / FADE)
        if fades_out:
            fade = min(fade, (length - self.time) / FADE)
        self.set_fade(max(0.0, fade))

        if name == "sleigh":
            self.fly_across(self.time)
        elif name == "house":
            self.visit(self.time)
        if name == "presents":
            self.unwrap(self.time, dt)
        else:
            self.outside(dt, name != "finale")
            self.move_dust(dt)
            self.snow(dt)
        if name == "finale":
            self.greet(self.time)
        if name in ("night", "finale"):
            self.shooting_star(self.time)
        else:
            self.streak.hidden = True
        self.sparkle(dt)

    def set_fade(self, fade):
        if fade == self.fade:
            return
        self.fade = fade
        for pal, colors in self.statics:
            pal.set_all([gfx.scale(c, fade) for c in colors])

    def place_camera(self):
        self.far.x = -int(self.cam * 0.5)
        self.near.x = -int(self.cam)

    def outside(self, dt, smoke):
        """Stars twinkle, windows glow, smoke rises from the chimney."""
        t = self.t
        pal = self.land_pal
        for i in range(3):
            pal[STAR1 + i] = self.lit(gfx.scale(0xE8F0FF, 0.6 + 0.4 * math.sin(t * (1.0 + 0.3 * i) + 2.0 * i)))
        pal[VILLAGE_WINDOW] = self.lit(gfx.mix(0xC07020, 0xFFD070, 0.6 + 0.4 * math.sin(t * 2.3)))
        pal[WINDOW] = self.lit(gfx.mix(0xE09030, 0xFFD070, 0.7 + 0.3 * math.sin(t * 3.1) * math.sin(t * 1.7)))
        pal[TREE_STAR] = self.lit(gfx.mix(0xA08020, 0xFFF0A0, 0.5 + 0.5 * math.sin(t * 4.0)))
        if not smoke:
            return
        x0 = HOUSE_X + 19.5
        y0 = 10.0
        for puff in self.puffs:
            circle = puff[0]
            puff[3] += dt
            if puff[3] < 0:
                circle.hidden = True
                continue
            if puff[3] > 3.2:
                puff[1], puff[2], puff[3] = x0, y0, 0.0
            age = puff[3]
            puff[1] += (1.2 + 0.8 * math.sin(t * 0.3)) * dt * min(1.0, age)
            puff[2] -= 2.2 * dt
            circle.hidden = False
            circle.x = int(puff[1] - self.cam)
            circle.y = int(puff[2])
            circle.color_index = min(4, 1 + int(age * 1.2))

    def fly_across(self, time):
        """Chapter 2: the sleigh crosses the sky in an arc, past the moon."""
        p = time / 8.5
        self.sleigh.hidden = p > 1.0
        self.sleigh.x = int(-28 + 96 * p)
        self.sleigh.y = int(10 - 7 * math.sin(math.pi * p))
        self.sleigh[0] = int(time * 5) % 2
        if p <= 1.0:
            self.trail(self.sleigh.x + 1, self.sleigh.y + 7)

    def visit(self, time):
        """Chapter 3: the view moves to the house, the sleigh lands in front of it and leaves."""
        self.cam = PAN * ease(time / 4.5)
        self.place_camera()
        door = HOUSE_X - self.cam  # screen x of the house
        if time < 4.5:
            self.sleigh.hidden = True
            return
        self.sleigh.hidden = False
        if time < 8.0:
            # glide down to the snow next to the house
            p = ease((time - 4.5) / 3.5)
            x, y = -30 + (door + 3) * p, -2 + 23 * p
            self.sleigh[0] = int(time * 5) % 2
            self.trail(int(x) + 1, int(y) + 7)
        elif time < 11.0:
            x, y = door - 27, 21  # standing in the snow, presents go in at the door
            self.sleigh[0] = 0
            if int(time * 10) % 8 == 0:
                self.burst(int(door) + 18, 23, 6)
        else:
            # off again, up and away to the right
            p = (time - 11.0) / 4.0
            x, y = door - 27 + 95 * p * p, 21 - 30 * p
            self.sleigh[0] = int(time * 5) % 2
            self.trail(int(x) + 1, int(y) + 7)
        self.sleigh.x = int(x)
        self.sleigh.y = int(y)

    def trail(self, x, y):
        if self.t < self.next_dust:
            return
        self.next_dust = self.t + 0.06
        for dot in self.dust:
            if dot[3] > 1.2:
                dot[1], dot[2], dot[3] = float(x + random.randrange(3)), float(y + random.randrange(2)), 0.0
                dot[0].hidden = False
                return

    def move_dust(self, dt):
        for dot in self.dust:
            if dot[3] > 1.2:
                continue
            dot[3] += dt
            dot[2] += 4.0 * dt
            if dot[3] > 1.2:
                dot[0].hidden = True
                continue
            dot[0].x = int(dot[1])
            dot[0].y = int(dot[2])
            dot[0].color_index = 1 + min(3, int(dot[3] * 3.3))

    def snow(self, dt):
        drift = 1.5 * math.sin(self.t * 0.17)
        for f in self.flakes:
            f[2] += f[3] * dt
            if f[2] >= 32:
                f[2] -= 33
                f[1] = random.uniform(0, 64)
            f[0].x = int(f[1] + drift + 1.2 * math.sin(self.t + f[3]))
            f[0].y = int(f[2])

    # --- chapter 4: the room ---------------------------------------------------------------

    def build_room(self):
        self.room_pal = self.pal(ROOM)
        b = displayio.Bitmap(64, 32, len(ROOM))
        # floor boards
        for x in range(64):
            b[x, 28] = FLOOR_TOP
            for y in range(29, 32):
                b[x, y] = FLOOR_DARK if (x + 7 * (y - 29)) % 11 == 0 else FLOOR
        # fireplace: bricks round a dark opening, a mantelpiece with two stockings
        for y in range(12, 28):
            for x in range(2, 20):
                course = (y - 12) // 2
                mortar = (y - 12) % 2 == 1 or (x + 3 * (course % 2)) % 6 == 0
                b[x, y] = MORTAR if mortar else (BRICK if (x // 6 + course) % 3 else BRICK_DARK)
        for y in range(18, 28):
            for x in range(6, 16):
                b[x, y] = SOOT
        for x in range(0, 22):
            b[x, 10] = MANTEL
            b[x, 11] = MANTEL_DARK
        for x in range(6, 16):
            b[x, 27] = LOG_WOOD if x % 4 else SOOT
        gfx.draw_art(b, STOCKING, {".": 0, "w": STOCKING_WHITE, "r": STOCKING_RED}, 3, 12)
        gfx.draw_art(b, STOCKING, {".": 0, "w": STOCKING_WHITE, "r": STOCKING_GREEN}, 14, 12)
        # window to the snowy night
        for y in range(4, 17):
            for x in range(23, 34):
                edge = x in (23, 28, 33) or y in (4, 10, 16)
                b[x, y] = SASH if edge else PANE
        for x, y in ((25, 6), (31, 7), (26, 12), (30, 14), (24, 14), (32, 12)):
            b[x, y] = PANE_SNOW
        self.tree(b, 48, 1)
        self.room.append(displayio.TileGrid(b, pixel_shader=self.room_pal.palette))

        sheet, w, h = gfx.sprite_sheet(FIRE, {".": 0, "1": 1, "2": 2, "3": 3, "4": 4})
        self.fire_pal = self.pal(FIRE_COLORS)
        self.fire = displayio.TileGrid(sheet, pixel_shader=self.fire_pal.palette, tile_width=w, tile_height=h,
                                       x=5, y=21)
        self.room.append(self.fire)

        self.presents = []
        for x, floor, w, h, box, ribbon in PRESENTS:
            bitmap = displayio.Bitmap(w, h + 2, 5)
            mid = w // 2
            for py in range(2, h + 2):
                for px in range(w):
                    if px == mid or py == 2 + h // 2:
                        bitmap[px, py] = 3  # ribbon
                    else:
                        bitmap[px, py] = 2 if px == w - 1 or py == h + 1 else 1
            for px, py in ((mid - 2, 0), (mid - 1, 1), (mid + 1, 1), (mid + 2, 0), (mid, 1)):
                if 0 <= px < w:
                    bitmap[px, py] = 4
            pal = self.pal((0, box, gfx.scale(box, 0.6), ribbon, gfx.mix(ribbon, 0xFFFFFF, 0.3)))
            grid = displayio.TileGrid(bitmap, pixel_shader=pal.palette, x=x, y=floor - h - 1)
            grid.hidden = True
            self.room.append(grid)
            self.presents.append(grid)

    def tree(self, b, cx, top):
        """A big Christmas tree in four tiers, with a garland, baubles, lights and a star."""
        tiers = ((top + 3, 5, 4), (top + 7, 6, 7), (top + 12, 6, 9), (top + 17, 7, 11))  # first row, rows, half width
        for first, rows, half in tiers:
            for i in range(rows):
                w = (half * (i + 2)) // (rows + 1)
                for x in range(cx - w, cx + w + 1):
                    shade = NEEDLE_LIT if x < cx - w // 3 else NEEDLE_DARK if x > cx + w // 2 else NEEDLE
                    b[x, first + i] = shade
            # a garland swings across each tier
            for x in range(cx - half + 2, cx + half - 1):
                y = first + rows - 2 - (x - cx + half) // 4
                if first <= y < first + rows and b[x, y] in (NEEDLE_LIT, NEEDLE, NEEDLE_DARK):
                    b[x, y] = GARLAND
        n = 0
        for first, rows, half in tiers:
            for i in range(1, rows, 2):
                w = (half * (i + 2)) // (rows + 1)
                for x in range(cx - w + 1, cx + w, 3):
                    n += 1
                    value = (BALL_RED, LIGHT1, BALL_BLUE, LIGHT2, BALL_GOLD, LIGHT3)[(n * 5 + i) % 6]
                    if b[x, first + i] != GARLAND:
                        b[x, first + i] = value
        for y in range(top + 24, top + 26):
            b[cx, y] = LOG_WOOD
        for y in range(top + 25, top + 27):
            for x in range(cx - 3, cx + 4):
                b[x, y] = POT_DARK if x == cx + 3 else POT
        gfx.draw_art(b, ("..g..", ".gSg.", "gSSSg", ".gSg.", "..g.."), {".": 0, "S": STAR, "g": STAR_GLOW},
                     cx - 2, top - 1)

    def unwrap(self, time, dt):
        """Chapter 4: lights twinkle, the fire flickers, presents drop in one after another."""
        t = self.t
        pal = self.room_pal
        for i, (index, color) in enumerate(((LIGHT1, 0xFFF0C0), (LIGHT2, 0xFFD040), (LIGHT3, 0xFF6080))):
            pal[index] = self.lit(gfx.scale(color, 0.35 + 0.65 * max(0.0, math.sin(t * (2.1 + 0.7 * i) + 2 * i))))
        pal[STAR] = self.lit(gfx.mix(0xFFC020, 0xFFFFD0, 0.5 + 0.5 * math.sin(t * 3.0)))
        pal[STAR_GLOW] = self.lit(gfx.scale(0xA07818, 0.6 + 0.4 * math.sin(t * 3.0)))
        if random.random() < dt * 8:
            self.fire[0] = random.randrange(3)
            flicker = random.uniform(0.75, 1.0)
            self.fire_pal[3] = self.lit(gfx.scale(FIRE_COLORS[3], flicker))
            self.fire_pal[4] = self.lit(gfx.scale(FIRE_COLORS[4], flicker))
        for i, grid in enumerate(self.presents):
            start = 2.5 + 2.0 * i
            if time < start:
                continue
            x, floor, w, h, box, ribbon = PRESENTS[i]
            rest = floor - h - 1
            fall = time - start
            if fall < 0.6:
                # falls in, bounces once
                grid.y = int(rest - 30 * (1 - fall / 0.45) ** 2) if fall < 0.45 else rest - int(2 * math.sin((fall - 0.45) / 0.15 * math.pi))
                grid.hidden = False
            elif not grid.hidden and grid.y != rest:
                grid.y = rest
                self.burst(x + w // 2 - 2, rest - 1, w)

    # --- chapter 5: the finale ---------------------------------------------------------------

    def build_finale(self):
        star = gfx.art_bitmap(BIG_STAR, {".": 0, "a": 1, "b": 2, "c": 3, "B": 4, "W": 5})
        self.star_pal = self.pal((0, 0x806010, 0xE0A020, 0x806030, 0xFFD040, 0xFFFFFF))
        self.ending.append(displayio.TileGrid(star, pixel_shader=self.star_pal.palette, x=26, y=0))
        text = displayio.Bitmap(64, 18, BANDS + 1)
        for line, y in (("Frohe", 0), ("Weihnachten", 10)):
            x = (64 - gfx.text_width(line)) // 2
            gfx.draw_text(text, line, x, y, lambda px, py: 1 + px * BANDS // 64)
        self.text_pal = gfx.Pal([0] * (BANDS + 1), transparent=(0,))
        self.ending.append(displayio.TileGrid(text, pixel_shader=self.text_pal.palette, y=12))

    def greet(self, time):
        """Chapter 5: the star shines, the words appear from left to right, a glint runs through them."""
        t = self.t
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        self.star_pal[1] = self.lit(gfx.mix(0x302008, 0xC09030, pulse))
        self.star_pal[3] = self.lit(gfx.mix(0x201808, 0x907040, 1 - pulse))
        for band in range(BANDS):
            # the bands light up one after the other, then a glint sweeps through every few seconds
            shown = min(1.0, max(0.0, (time - 1.2) * 5.0 - band * 0.5))
            glint = max(0.0, math.cos(((band / BANDS) - (time - 4.0) * 0.4) * 2 * math.pi)) ** 16
            color = gfx.mix(0xFFB020, 0xFFFFFF, glint * 0.7 if time > 4.0 else 0.0)
            self.text_pal[band + 1] = self.lit(gfx.scale(color, shown))

    def shooting_star(self, time):
        """Every five seconds a shooting star, each time somewhere else."""
        p = (time % 5.0) / 0.8
        if 1.5 < time and p < 1.0:
            self.streak.hidden = False
            self.streak.x = int(-6 + 40 * p) + (int(time / 5.0) * 23) % 30
            self.streak.y = int(1 + 6 * p)
        else:
            self.streak.hidden = True

    # --- sparkles ----------------------------------------------------------------------------

    def burst(self, x, y, spread):
        for glint in self.glints:
            if glint[1] > 0.5:
                glint[0].x = x + random.randrange(-2, spread)
                glint[0].y = y - random.randrange(0, 5)
                glint[1] = -random.uniform(0.0, 0.2)
                return

    def sparkle(self, dt):
        for glint in self.glints:
            glint[1] += dt
            step = int(glint[1] / 0.08) if glint[1] >= 0 else -1
            if 0 <= step < 5:
                glint[0].hidden = False
                glint[0][0] = (0, 1, 2, 1, 0)[step]
            else:
                glint[0].hidden = True
