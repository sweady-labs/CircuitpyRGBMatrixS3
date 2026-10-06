"""Schild: a round shield in red, white and blue with a white star, spinning in 3D.

The shield is drawn once, front and back, into two bitmaps. Turning it is a horizontal squash:
each frame every screen column copies one column of the picture (bitmaptools.blit), about 30
small copies. Light and shine are palette animation: every pixel belongs to a material (red,
white, blue, star, rim, ...) and to a diagonal band across the shield, and the colors of the bands
follow the angle, so a highlight wanders over the metal while it turns. Now and then the shield
stops facing you, and a shine sweeps across it.
"""
import math
import random

import bitmaptools
import displayio

from app import gfx

FPS = 25
PREVIEW_AT = 0.4
SIZE = 30  # the shield picture is SIZE x SIZE pixels
R = SIZE / 2
X0, Y0 = 17, 1  # its top left corner on the screen
BANDS = 12  # diagonal bands for light and shine

RED, WHITE, BLUE, STAR, RIM, METAL, GROOVE, STRAP, RIVET = range(9)
BASE = (0xD01828, 0xC0C6D4, 0x1E3CCC, 0xF4F6FF, 0x7A1018, 0x707888, 0x3E434E, 0x7A4220, 0xD8D8D8)
FRONT = (RED, WHITE, BLUE, STAR, RIM)
BACK = (METAL, GROOVE, STRAP, RIVET)
MATERIALS = 9
STARS = 22  # twinkling stars in the background
SPARKLE = ("...1...", "...2...", "...2...", "1223221", "...2...", "...2...", "...1...")


# the star in the blue middle, drawn by hand (crisper than computed): 12 x 12 pixels from (9, 9)
STAR_ART = (
    "............",
    "............",
    ".....##.....",
    ".....##.....",
    "....####....",
    ".##########.",
    "..########..",
    "....####....",
    "...######...",
    "...##..##...",
    "..#......#..",
    "............",
)


def index(material, band):
    return 1 + material * BANDS + band


class Scene:
    def __init__(self, group, settings):
        # background: a few faint stars that twinkle slowly
        self.sky, self.sky_pal = gfx.canvas(group, [0, 0, 0, 0])
        for _ in range(STARS):
            x, y = random.randrange(64), random.randrange(32)
            if not (X0 - 1 <= x <= X0 + SIZE and Y0 - 1 <= y <= Y0 + SIZE):
                self.sky[x, y] = random.randint(1, 3)

        self.pal = gfx.Pal([0] * (1 + MATERIALS * BANDS), transparent=(0,))
        self.canvas = displayio.Bitmap(64, 32, len(self.pal))
        group.append(displayio.TileGrid(self.canvas, pixel_shader=self.pal.palette))
        self.front = self.picture(True)
        self.back = self.picture(False)

        # a sparkle on the rim at the top left, where the sweeping shine leaves the shield
        sheet = gfx.art_bitmap(SPARKLE, {".": 0, "1": 1, "2": 2, "3": 3})
        self.sparkle_pal = gfx.Pal([0, 0, 0, 0], transparent=(0,))
        self.sparkle = displayio.TileGrid(sheet, pixel_shader=self.sparkle_pal.palette, x=X0 + 1, y=Y0 + 1)
        self.sparkle.hidden = True
        group.append(self.sparkle)

        self.angle = 0.0  # 0: the front faces you
        self.speed = 0.0  # radians per second
        self.turn = 1
        self.mode = "rest"
        self.clock = 0.0
        self.rest_time = 3.0
        self.time = 0.0
        self.drawn = None  # angle and light of the last frame: while resting nothing needs redoing
        self.lit = None

    # --- Pictures ---------------------------------------------------------------------

    def picture(self, front):
        bitmap = displayio.Bitmap(SIZE, SIZE, len(self.pal))
        for y in range(SIZE):
            for x in range(SIZE):
                dx, dy = x + 0.5 - R, y + 0.5 - R
                d = math.sqrt(dx * dx + dy * dy)
                if d > R:
                    continue
                if d > R - 1.0:
                    material = RIM if front else GROOVE
                elif front:
                    if d > 11.6:
                        material = RED
                    elif d > 8.7:
                        material = WHITE
                    elif d > 6.0:
                        material = RED
                    else:
                        material = STAR if STAR_ART[y - 9][x - 9] == "#" else BLUE
                else:
                    material = self.back_material(dx, dy, d)
                # bands run diagonally from the top left (lit) to the bottom right
                band = min(BANDS - 1, int((x + 0.6 * y) / (SIZE * 1.6) * BANDS))
                bitmap[x, y] = index(material, band)
        return bitmap

    def back_material(self, dx, dy, d):
        """Inside of the shield: bare metal with two leather straps held by rivets."""
        for top in (-4.5, 2.5):
            if top <= dy < top + 2.5 and abs(dx) < 8.5:
                return RIVET if abs(abs(dx) - 7.0) < 0.8 and dy < top + 1.5 else STRAP
        if 9.5 < d < 10.5:
            return GROOVE  # a groove in the bowl
        return METAL

    # --- Motion -----------------------------------------------------------------------

    def move(self, dt):
        """Rest facing you, speed up, spin a few turns, slow down to face you again."""
        self.clock += dt
        if self.mode == "rest":
            if self.clock > self.rest_time:
                self.mode = "spin"
                self.clock = 0.0
                self.turn = random.choice((-1, 1))
                self.top = random.uniform(4.0, 7.5)  # radians per second
                self.spin_time = random.uniform(2.0, 5.0)
        elif self.mode == "spin":
            self.speed = min(self.top, self.speed + 5.0 * dt)
            self.angle += self.turn * self.speed * dt
            if self.clock > self.spin_time:
                # slow down evenly so that it stops exactly facing you, at least one turn later
                full = 2 * math.pi
                target = (math.floor(self.angle / full) + (2 if self.turn > 0 else -1)) * full
                self.brake_from = self.angle
                self.brake_way = target - self.angle
                self.brake_time = 2 * abs(self.brake_way) / self.speed
                self.mode = "brake"
                self.clock = 0.0
        else:
            u = min(1.0, self.clock / self.brake_time)
            self.angle = self.brake_from + self.brake_way * (1 - (1 - u) * (1 - u))
            if u >= 1.0:
                self.angle = 0.0
                self.speed = 0.0
                self.mode = "rest"
                self.clock = 0.0
                self.rest_time = random.uniform(3.0, 5.0)

    # --- Drawing ----------------------------------------------------------------------

    def draw(self):
        if self.angle == self.drawn:
            return
        self.drawn = self.angle
        c = math.cos(self.angle)
        width = abs(c)
        source = self.front if c >= 0 else self.back
        canvas = self.canvas
        bitmaptools.fill_region(canvas, X0, Y0, X0 + SIZE, Y0 + SIZE, 0)
        if width < 0.06:  # edge on: only the rim shows
            bitmaptools.fill_region(canvas, X0 + 14, Y0 + 3, X0 + 16, Y0 + SIZE - 3, index(RIM, 4))
            return
        for column in range(SIZE):
            u = (column + 0.5 - R) / width + R  # column of the picture seen here
            if 0 <= u < SIZE:
                bitmaptools.blit(canvas, source, X0 + column, Y0, x1=int(u), y1=0, x2=int(u) + 1, y2=SIZE)

    def light(self):
        """Colors for the side you see: brighter top left, darker when turned away, plus a shine."""
        c = math.cos(self.angle)
        s = math.sin(self.angle)
        facing = 0.45 + 0.55 * abs(c)
        if self.mode == "rest":
            # a shine sweeps across while it rests, then a calm glint stays at the top left
            sweep = self.clock - 0.6
            shine = -3.0 + sweep * 10.0 if 0 < sweep < 1.8 else 3.0
            strength = 0.6 if 0 < sweep < 1.8 else 0.2
        else:
            shine = (BANDS - 1) * (0.45 - 0.55 * s * self.turn)
            strength = 0.5 * abs(c) ** 3
        if c < 0:
            strength *= 0.5  # the inside is a bowl and catches less light
        if (c, shine, strength) != self.lit:
            self.lit = (c, shine, strength)
            shades = [(1.12 - 0.5 * band / (BANDS - 1)) * facing for band in range(BANDS)]
            glints = [strength * math.exp(-(band - shine) ** 2) for band in range(BANDS)]
            for material in (FRONT if c >= 0 else BACK):
                base = BASE[material]
                for band in range(BANDS):
                    self.pal[index(material, band)] = gfx.mix(gfx.scale(base, shades[band]), 0xFFFFFF, glints[band])
        # sparkle when the sweeping shine passes the top left
        spark = 0.0
        if self.mode == "rest":
            spark = max(0.0, 1.0 - abs(self.clock - 0.6 - 0.35) * 4.0)
        self.sparkle.hidden = spark <= 0
        for i, level in ((1, 0.3), (2, 0.65), (3, 1.0)):
            self.sparkle_pal[i] = gfx.scale(0xFFFFFF, spark * level)

    def frame(self, dt):
        self.time += dt
        self.move(dt)
        self.draw()
        self.light()
        for i in range(1, 4):
            self.sky_pal[i] = gfx.scale(0x8090B0, 0.25 + 0.2 * math.sin(self.time * (0.7 + 0.3 * i) + i * 2.1))
