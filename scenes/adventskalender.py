"""Adventskalender: 24 little doors; in December the doors up to today are open and show pictures.

Today's door has a gold frame; now and then it opens, sparkles, and its picture is shown large
with the date. Before December all doors are closed, a gleam runs over their gilded edges and
the calendar says how many days are left until the first door ("noch 56 Tage"). After the 24th
every door is open. Without a clock the doors open one after another, as a demonstration.

The doors are drawn into one bitmap and only redrawn when one changes; everything else is palette.
"""
import math
import random

import displayio

from app import clock, font, gfx

FPS = 20
PREVIEW_AT = 4.5

COLS = 8  # three rows of eight doors
# door number of each cell, row by row: shuffled like on a real calendar
ORDER = (7, 15, 1, 20, 11, 3, 18, 9,
         13, 4, 22, 24, 6, 16, 2, 21,
         19, 10, 5, 14, 23, 8, 12, 17)

DIGITS = ("###|#.#|#.#|#.#|###", ".#.|##.|.#.|.#.|###", "###|..#|###|#..|###", "###|..#|.##|..#|###",
          "#.#|#.#|###|..#|..#", "###|#..|###|..#|###", "###|#..|###|#.#|###", "###|..#|.#.|.#.|.#.",
          "###|#.#|###|#.#|###", "###|#.#|###|..#|###")

# palette of the calendar bitmap
DOOR = 1  # 4 door colors x (light, base, shadow)
NUMBER = 13
INSIDE = 14
FRAME = 15  # today's frame
TRIM = 16  # gilded top edge of the doors, one entry per column for the gleam
ICON = TRIM + COLS  # picture colors
DOOR_COLORS = ((0xD03040, 0x9A1424, 0x500810), (0x30A050, 0x0E6A2E, 0x063A18),
               (0x4070D0, 0x1C3C90, 0x0C1E4C), (0xB05AB0, 0x6E2470, 0x3A103C))
ICON_KEYS = "WRrGgYyOBbCUPVKSTwLs"
ICON_COLORS = (0xFFFFFF, 0xE01828, 0x801018, 0x20B040, 0x0C6024, 0xFFD030, 0xB08010, 0xFF8020, 0xA86030,
               0x5A3014, 0x90D0FF, 0x2860E0, 0xFF80B0, 0xA040E0, 0x404A68, 0xF0C8A0, 0xD8A060, 0x9098B0,
               0xFFE8A0, 0xC08040)
PICTURES = (
    ("...Y...", "..YYY..", "YYYYYYY", ".YYWYY.", "..YYY..", ".YY.YY.", "YY...YY"),  # 1 star
    ("G.....G", "GG...GG", "GGG.GGG", ".GGRGG.", "..RWR..", "..RRR..", "......."),  # 2 holly
    ("...y...", "..YYY..", ".YWYYY.", ".YWYYY.", ".YYYYY.", "YYYYYYY", "...R..."),  # 3 bell
    ("..KKK..", ".KKKKK.", "..WWW..", "..WWO..", ".WWRWW.", ".WWWWW.", "..WWW.."),  # 4 snowman
    (".RR.RR.", "RWRRRRR", "RRRRRRR", "RRRRRRR", ".RRRRR.", "..RRR..", "...R..."),  # 5 heart
    (".WWWW..", ".RRRR..", ".RRRR..", ".RRRR..", ".RRRRRR", ".RRRRRR", ".bbbbbb"),  # 6 Nikolaus boot
    ("...O...", "..OYO..", "...b...", "..RRR..", "..WRR..", "..RRR..", ".yyyyy."),  # 7 candle
    (".Y...Y.", "..YYY..", "UUUYUUU", "UUUYUUU", "YYYYYYY", "UUUYUUU", "UUUYUUU"),  # 8 present
    ("..RWR..", ".W...W.", ".R...R.", ".....W.", ".....R.", ".....W.", ".....R."),  # 9 candy cane
    ("...y...", "..yYy..", ".VVVVV.", "VWVVVVV", "VVVVVVV", ".VVVVV.", "..VVV.."),  # 10 bauble
    ("..BBB..", "..WBW..", "BBBBBBB", "..BWB..", "..BBB..", ".BB.BB.", "BB...BB"),  # 11 gingerbread
    ("...C...", ".C.C.C.", "..CCC..", "CCCWCCC", "..CCC..", ".C.C.C.", "...C..."),  # 12 snowflake
    ("..YYY..", ".YY....", "YY...W.", "YY.....", "YY..W..", ".YY....", "..YYY.."),  # 13 moon
    ("..YYY..", "..ySy..", "LL.W.LL", "LLWWWLL", ".LWWWL.", ".WWWWW.", "WWWWWWW"),  # 14 angel
    (".RRR...", "RRRRR..", "RRRRR.R", "RRRRRRR", "RRRRRR.", "WWWWW..", "WWWWW.."),  # 15 mitten
    ("BB...BB", "BBBBBBB", "BKBBBKB", "BBSSSBB", "BBSKSBB", ".BBBBB.", "..BBB.."),  # 16 teddy
    ("T.T.T.T", ".TT.TT.", "..BBB..", ".BKBKB.", "..BBB..", "..BBB..", "..BRB.."),  # 17 reindeer
    ("....W..", "...RR..", "..RRR..", "..RRRR.", ".RRRRR.", "WWWWWWW", "WWWWWWW"),  # 18 Santa's hat
    ("..TTT..", ".TbTTT.", "TTTTbTT", "TbTTTTT", "TTTbTTT", ".TTTTb.", "..TTT.."),  # 19 biscuit
    (".......", "R....R.", "RRRRRR.", "RRRRRR.", ".Y..Y..", "YYYYYYY", "......Y"),  # 20 sledge
    ("...W...", "..WWW..", ".WWWWW.", "WWWWWWW", ".BYBbB.", ".BBBbB.", ".BBBbB."),  # 21 house
    ("..KKK..", ".KWKWK.", ".KKOKK.", "KKWWWKK", "KKWWWKK", ".KWWWK.", ".OO.OO."),  # 22 penguin
    (".w..w..", "..w..w.", "RRRRR..", "RRRRRRR", "RRRRR.R", "RRRRRRR", ".RRR..."),  # 23 cocoa
    ("...Y...", "..GGG..", ".GGRGG.", "..GGG..", ".GYGGG.", "GGGGRGG", "...b..."),  # 24 tree
)
GLINT = (
    (".....", ".....", "..a..", ".....", "....."),
    (".....", "..b..", ".bab.", "..b..", "....."),
    ("..b..", "..a..", "baaab", "..a..", "..b.."),
)


def day_number(year, month, day):
    """Days since a fixed date long ago; the difference of two is the days between them."""
    if month < 3:
        year -= 1
        month += 12
    return 365 * year + year // 4 - year // 100 + year // 400 + (153 * (month - 3) + 2) // 5 + day


def cell_of(door):
    i = ORDER.index(door)
    return 8 * (i % COLS), 1 + 10 * (i // COLS), i % COLS, i // COLS


class Scene:
    def __init__(self, group, settings):
        colors = [0] * (ICON + len(ICON_COLORS))
        for k, shades in enumerate(DOOR_COLORS):
            colors[DOOR + 3 * k:DOOR + 3 * k + 3] = shades
        colors[NUMBER] = 0xFFE8B0
        colors[INSIDE] = 0x140608
        colors[ICON:] = ICON_COLORS
        self.colors = colors
        self.bitmap, self.pal = gfx.canvas(group, colors)
        self.keys = {".": INSIDE}  # picture keys in the calendar, and in the big picture
        self.zoom_keys = {".": 0}
        for i, key in enumerate(ICON_KEYS):
            self.keys[key] = ICON + i
            self.zoom_keys[key] = 1 + i

        # the big picture: one 7x7 picture, three times enlarged; and the text beside the calendar
        self.zoom_pal = gfx.Pal([0] + list(ICON_COLORS), transparent=(0,))
        self.zoom_bitmap = displayio.Bitmap(7, 7, len(self.zoom_pal))
        self.zoom = displayio.Group(scale=3, x=21, y=0)
        self.zoom.append(displayio.TileGrid(self.zoom_bitmap, pixel_shader=self.zoom_pal.palette))
        self.zoom.hidden = True
        group.append(self.zoom)
        self.text_pal = gfx.Pal((0, 0xFFF0D0, 0xFFC830), transparent=(0,))
        self.text = displayio.Bitmap(64, 32, 3)
        self.text_grid = displayio.TileGrid(self.text, pixel_shader=self.text_pal.palette)
        self.text_grid.hidden = True
        group.append(self.text_grid)
        sheet, w, h = gfx.sprite_sheet(GLINT, {".": 0, "a": 1, "b": 2})
        self.glint_pal = gfx.Pal((0, 0xFFFFFF, 0xFFE0A0), transparent=(0,))
        self.glints = []
        for _ in range(3):
            grid = displayio.TileGrid(sheet, pixel_shader=self.glint_pal.palette, tile_width=w, tile_height=h)
            grid.hidden = True
            group.append(grid)
            self.glints.append([grid, 9.0])  # grid, age

        self.mode = None
        self.today = 0
        self.left = 0  # days until 1 December
        self.open = set()  # doors that stand open
        self.moving = None  # [door, seconds, opening] while a door swings
        self.step = 0  # how far the little story of the mode has got
        self.wait = 0.0  # seconds until its next step
        self.t = 0.0
        self.dim = 1.0
        self.target_dim = 1.0
        self.check = 30.0  # seconds until the date is checked again
        self.look_at_date()

    # --- drawing ---------------------------------------------------------------------------

    def draw_door(self, door, leaf=7):
        """leaf: width of the door still closed, 7 = shut, 0 = wide open."""
        b = self.bitmap
        x, y, col, row = cell_of(door)
        k = (col + 2 * row) % 4
        light, base, shadow = DOOR + 3 * k, DOOR + 3 * k + 1, DOOR + 3 * k + 2
        if leaf < 7:
            # inside: the picture, with the door leaf swung open to the left
            for py in range(y, y + 9):
                for px in range(x, x + 7):
                    b[px, py] = INSIDE
            gfx.draw_art(b, PICTURES[door - 1], self.keys, x, y + 1)
            if leaf == 0 and x > 0:
                for py in range(y, y + 9):
                    b[x - 1, py] = light
        if leaf > 0:
            for py in range(y, y + 9):
                for px in range(x, x + leaf):
                    b[px, py] = shadow if py == y + 8 or px == x + leaf - 1 else base
            for px in range(x, x + leaf):
                b[px, y] = TRIM + col
            if leaf == 7:
                text = str(door)
                dx = x + (2 if door < 10 else 0)
                for digit in text:
                    for gy, line in enumerate(DIGITS[int(digit)].split("|")):
                        for gx, c in enumerate(line):
                            if c == "#":
                                b[dx + gx, y + 2 + gy] = NUMBER
                    dx += 4

    def draw_all(self):
        self.bitmap.fill(0)
        for door in range(1, 25):
            self.draw_door(door, 0 if door in self.open else 7)
        if 1 <= self.today <= 24:
            self.frame_today()

    def frame_today(self):
        x, y, col, row = cell_of(self.today)
        for px in range(x - 1, x + 8):
            for py in (y - 1, y + 9):
                if 0 <= px < 64 and 0 <= py < 32:
                    self.bitmap[px, py] = FRAME
        for py in range(y, y + 9):
            if x > 0 and self.today not in self.open:
                self.bitmap[x - 1, py] = FRAME
            self.bitmap[x + 7, py] = FRAME

    def write(self, lines):
        """lines: (text, y, value, table), centred; value 1 cream, 2 gold."""
        self.text.fill(0)
        for text, y, value, table in lines:
            gfx.draw_text(self.text, text, (64 - gfx.text_width(text, table)) // 2, y, value, table)

    # --- what to show when -------------------------------------------------------------------

    def look_at_date(self):
        local = clock.now()
        if local is None:
            mode, today, left = "demo", 0, 0
        elif local.tm_mon == 12 and local.tm_mday <= 24:
            mode, today, left = "december", local.tm_mday, 0
        elif local.tm_mon == 12:
            mode, today, left = "after", 25, 0
        else:
            mode, today = "before", 0
            left = day_number(local.tm_year, 12, 1) - day_number(local.tm_year, local.tm_mon, local.tm_mday)
        if (mode, today) != (self.mode, self.today):
            self.mode, self.today = mode, today
            if mode == "december":
                self.open = set(range(1, today))
            elif mode == "after":
                self.open = set(range(1, 25))
            else:
                self.open = set()
            self.moving = None
            self.hide_reveal()
            self.step = 0
            self.wait = 3.0
            self.draw_all()
        self.left = left

    def frame(self, dt):
        self.t += dt
        self.check -= dt
        if self.check <= 0:
            self.check = 30.0
            self.look_at_date()
        self.wait -= dt
        if self.wait <= 0:
            self.next_step()
        if self.moving:
            self.swing(dt)
        self.lights(dt)

    def next_step(self):
        """Advance the little story of the current mode."""
        mode = self.mode
        if mode == "demo":
            # open the doors one after another, then close them all and start again
            closed = [d for d in range(1, 25) if d not in self.open]
            if closed:
                self.moving = [closed[0], 0.0, True]
                self.wait = 2.2
            elif self.target_dim == 1.0:
                self.target_dim = 0.0  # fade out first
                self.wait = 1.0
            else:
                self.open = set()
                self.draw_all()
                self.target_dim = 1.0
                self.wait = 3.0
        elif mode == "before":
            # the calendar for a while, then the countdown
            if self.step % 2 == 0:
                days = self.left
                self.write((("noch", 0, 1, None), (str(days), 7, 2, font.BIG),
                            ("Tag" if days == 1 else "Tage", 23, 1, None)))
                self.show_text(True)
                self.wait = 7.0
            else:
                self.show_text(False)
                self.wait = 14.0
            self.step += 1
        elif mode == "december":
            # today's door opens, its picture is shown large, later the door closes again
            phase = self.step % 4
            if phase == 0:
                self.moving = [self.today, 0.0, True]
                self.wait = 2.0
            elif phase == 1:
                self.reveal(self.today)
                self.wait = 5.0
            elif phase == 2:
                self.hide_reveal()
                self.wait = 20.0
            else:
                self.moving = [self.today, 0.0, False]
                self.wait = 8.0
            self.step += 1
        elif mode == "after":
            if self.step % 2 == 0:
                self.reveal(random.randrange(1, 25))
                self.wait = 5.0
            else:
                self.hide_reveal()
                self.wait = 14.0
            self.step += 1

    def swing(self, dt):
        """A door swings open (with glints when it is open) or shut, in about half a second."""
        door, time, opening = self.moving
        time += dt
        self.moving[1] = time
        shut = min(7, int(time * 12))
        leaf = 7 - shut if opening else shut
        self.draw_door(door, leaf)
        if shut < 7:
            return
        self.moving = None
        if opening:
            self.open.add(door)
            x, y, col, row = cell_of(door)
            for glint, (gx, gy) in zip(self.glints, ((x - 3, y - 2), (x + 4, y + 1), (x, y + 6))):
                glint[0].x, glint[0].y = gx, gy
                glint[1] = -random.uniform(0.0, 0.25)
        else:
            self.open.discard(door)
        if door == self.today:
            self.frame_today()

    def reveal(self, door):
        self.zoom_bitmap.fill(0)
        gfx.draw_art(self.zoom_bitmap, PICTURES[door - 1], self.zoom_keys, 0, 0)
        self.write((("%d. Dezember" % door, 23, 1, None),))
        self.zoom.hidden = False
        self.show_text(True)

    def hide_reveal(self):
        self.zoom.hidden = True
        self.show_text(False)

    def show_text(self, on):
        self.text_grid.hidden = not on
        self.target_dim = 0.18 if on else 1.0

    def lights(self, dt):
        # the calendar dims softly behind text and big picture
        target = self.target_dim
        if self.dim != target:
            step = dt * 2.0
            self.dim = min(target, self.dim + step) if target > self.dim else max(target, self.dim - step)
            self.pal.set_all([gfx.scale(c, self.dim) for c in self.colors])
        # a gleam runs over the gilded door edges, today's frame glows
        sweep = (self.t * 2.2) % 14 - 3
        for col in range(COLS):
            gleam = max(0.0, 1.0 - abs(col - sweep) * 0.6)
            self.pal[TRIM + col] = gfx.scale(gfx.mix(0xA07020, 0xFFF0B0, gleam), self.dim)
        self.pal[FRAME] = gfx.scale(gfx.mix(0x806010, 0xFFD040, 0.5 + 0.5 * math.sin(self.t * 3.0)), self.dim)
        for glint in self.glints:
            glint[1] += dt
            step = int(glint[1] / 0.08) if glint[1] >= 0 else -1
            if 0 <= step < 5:
                glint[0].hidden = False
                glint[0][0] = (0, 1, 2, 1, 0)[step]
            else:
                glint[0].hidden = True
