"""Sternenhimmel: softly twinkling stars, the Milky Way, the moon in today's phase, now and then a shooting star.

Stars in many colors over dark hills, the Milky Way rising from the hills on the right. The sky
is drawn once and twinkles only through its palette: every bright star has its own palette entry
whose brightness follows two slow waves, the smaller stars share a few entries. The moon is drawn
for the real phase (from the clock) and drawn again when the day changes. A shooting star is a
short line with a fading tail in a layer of its own, drawn again every frame while it flies.
"""
import math
import random
import time

import displayio

from app import clock, gfx

FPS = 20
PREVIEW_AT = 2.0
NEW_MOON = 947182440  # 2000-01-06 18:14 UTC, a new moon
SYNODIC_MONTH = 29.530589 * 86400
MOON_X, MOON_Y, MOON_R = 54, 8, 5.3  # middle and radius of the moon
TAIL = 10  # pixels of a shooting star's tail

# star colors, most of them white or bluish like in the real sky
COLORS = (0xC8D8FF, 0xC8D8FF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFF4DC, 0xFFF4DC, 0xFFE0A0, 0xFFB070)
# Dim colors keep their green at least 1.2 times their red: the LEDs light dim green later than
# red and blue, and a dim grey would otherwise turn purple.
GLOW = (0x1C2238, 0x283048, 0x384458, 0x46543C)  # Milky Way from faint to bright, the last one warmer
FAINT = (0x64787F, 0x808080, 0x807860)  # faint stars: bluish, white, warm
BLACK, GLOW1, FAINT1 = 0, 1, 5  # palette: glow 1-4, faint stars 5-7
GROUP1 = 8  # small stars twinkle in GROUPS groups
GROUPS = 6
BRIGHT1 = GROUP1 + GROUPS  # from here two entries per bright star: the star and its rays
# transparent, dark side (faint earthshine), terminator, maria, rim, brightest
MOON_COLORS = (0, 0x161C34, 0x4A4640, 0x9C9888, 0xD0C8B4, 0xFFF6E0)
MARIA = ((-2, -2), (-1, -2), (-2, -1), (-1, -1), (1, -1), (1, 0), (2, 0), (2, 1), (-1, 2), (0, 2))


def moon_phase():
    """0 = new moon, 0.25 = first quarter, 0.5 = full moon, 0.75 = last quarter."""
    local = clock.now()
    if local is None:
        return 0.3  # waxing until the clock is set
    return ((time.mktime(local) - NEW_MOON) / SYNODIC_MONTH) % 1.0


class Scene:
    def __init__(self, group, settings):
        self.bright = [(random.choice(COLORS), random.uniform(0.75, 1.0)) for _ in range(12)]
        colors = [0] + list(GLOW) + list(FAINT)
        colors += [gfx.scale(random.choice(COLORS), 0.68) for _ in range(GROUPS)]
        colors += [0] * (2 * len(self.bright))
        self.sky, self.pal = gfx.canvas(group, colors)
        self.base = list(colors)  # palette colors without twinkle
        self.waves = [(random.uniform(0.3, 1.1), random.uniform(1.3, 3.1), random.uniform(0, 6.3))
                      for _ in range(len(colors))]
        # gentle hills, a little higher on the right
        self.hills = [int(29.0 - 3.0 * math.exp(-((x - 47) / 10.0) ** 2) - 0.8 * math.sin(x / 5.0))
                      for x in range(64)]
        self.draw_sky()

        self.moon = displayio.Bitmap(13, 13, len(MOON_COLORS))
        self.moon_pal = gfx.Pal(MOON_COLORS, transparent=(0,))
        grid = displayio.TileGrid(self.moon, pixel_shader=self.moon_pal.palette)
        grid.x, grid.y = MOON_X - 6, MOON_Y - 6
        group.append(grid)
        self.moon_day = None
        self.moon_wait = 60.0
        self.draw_moon()

        self.meteor = displayio.Bitmap(64, 32, TAIL + 1)
        self.meteor_pal = gfx.Pal([0] * (TAIL + 1), transparent=(0,))
        group.append(displayio.TileGrid(self.meteor, pixel_shader=self.meteor_pal.palette))
        self.flight = None
        self.wait = random.uniform(4.0, 10.0)
        self.t = 0.0

    # --- drawn once ------------------------------------------------------------------------

    def free(self, x, y):
        """A pixel of open sky: above the hills, away from the moon, not taken by a star yet."""
        if not (0 <= x < 64 and 0 <= y < self.hills[x]):
            return False
        if (x - MOON_X) ** 2 + (y - MOON_Y) ** 2 < (MOON_R + 2.5) ** 2:
            return False
        return self.sky[x, y] < FAINT1

    def draw_sky(self):
        sky = self.sky
        # Milky Way: a grainy band rising from the hills on the right to the upper left, brightest
        # near the hills, with a dark rift along its middle
        for x in range(64):
            for y in range(self.hills[x]):
                along = 0.875 * (47 - x) + 0.484 * (20 - y)
                across = 0.484 * (x - 47) - 0.875 * (y - 20) + 1.5 * math.sin(along / 10.0)
                glow = math.exp(-across * across / 20.0) * (0.45 + 0.45 * math.exp(-(along / 16.0) ** 2))
                glow *= 1.0 - 0.6 * math.exp(-(across - 0.7) ** 2 / 1.4) * min(1.0, along / 8.0)
                level = int(glow * 4.4 + random.random() * 1.2 - 0.8)
                if level > 0:
                    sky[x, y] = GLOW1 + min(level, 4 if along < 16 else 3) - 1
                if random.random() < glow * 0.13:
                    sky[x, y] = FAINT1 + random.randrange(3)
        # stars: faint ones, small twinkling ones, and bright ones with rays
        for _ in range(45):
            x, y = random.randrange(64), random.randrange(28)
            if self.free(x, y):
                sky[x, y] = FAINT1 + random.randrange(3)
        for _ in range(28):
            x, y = random.randrange(64), random.randrange(27)
            if self.free(x, y):
                sky[x, y] = GROUP1 + random.randrange(GROUPS)
        for i in range(len(self.bright)):
            for _ in range(20):  # a few tries to find room
                x, y = random.randrange(2, 62), random.randrange(1, 24)
                if all(self.free(x + dx, y + dy) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))):
                    sky[x, y] = BRIGHT1 + 2 * i
                    if i < 4:  # the brightest have short rays
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            sky[x + dx, y + dy] = BRIGHT1 + 2 * i + 1
                    break
        # the dark hills
        for x in range(64):
            for y in range(self.hills[x], 32):
                sky[x, y] = BLACK

    def draw_moon(self):
        phase = moon_phase()
        local = clock.now()
        self.moon_day = local.tm_mday if local else None
        light = math.cos(2 * math.pi * phase)
        for py in range(13):
            for px in range(13):
                dx, dy = px - 6, py - 6
                r2 = dx * dx + dy * dy
                if r2 > MOON_R * MOON_R:
                    self.moon[px, py] = 0
                    continue
                edge = math.sqrt(MOON_R * MOON_R - dy * dy) * light  # x of the terminator in this row
                lit = dx - edge if phase < 0.5 else -edge - dx
                if lit < -0.5:
                    value = 1  # the dark side, lit faintly by the earth
                elif lit < 0.5:
                    value = 2
                elif (dx, dy) in MARIA:
                    value = 3
                else:
                    value = 5 if r2 < (MOON_R - 1.4) ** 2 else 4  # a little darker towards the rim
                self.moon[px, py] = value

    # --- every frame -----------------------------------------------------------------------

    def frame(self, dt):
        self.t += dt
        t = self.t
        # small stars twinkle in groups, bright stars and their rays one by one
        for i in range(GROUP1, GROUP1 + GROUPS):
            slow, fast, phase = self.waves[i]
            dip = (0.5 + 0.5 * math.sin(t * slow + phase)) * (0.5 + 0.5 * math.sin(t * fast + phase))
            self.pal[i] = gfx.scale(self.base[i], 1.0 - 0.35 * dip)
        for i, (color, strength) in enumerate(self.bright):
            slow, fast, phase = self.waves[BRIGHT1 + 2 * i]
            dip = (0.5 + 0.5 * math.sin(t * slow + phase)) * (0.5 + 0.5 * math.sin(t * fast + phase))
            star = gfx.scale(color, strength * (1.0 - 0.3 * dip))
            self.pal[BRIGHT1 + 2 * i] = star
            if i < 4:
                self.pal[BRIGHT1 + 2 * i + 1] = gfx.scale(star, 0.34 - 0.12 * dip)

        self.fly(dt)
        self.moon_wait -= dt
        if self.moon_wait <= 0:  # once a minute: a new day brings a new moon
            self.moon_wait = 60.0
            local = clock.now()
            if local is not None and local.tm_mday != self.moon_day:
                self.draw_moon()

    def fly(self, dt):
        """Now and then a shooting star: a bright head with a fading tail, gone after a moment."""
        if self.flight is None:
            self.wait -= dt
            if self.wait > 0:
                return
            angle = random.uniform(0.25, 0.75)
            speed = random.uniform(45.0, 75.0)
            x = random.uniform(8.0, 50.0)
            direction = 1 if x < 30 else -1
            self.flight = [x, random.uniform(1.0, 9.0), math.cos(angle) * speed * direction,
                           math.sin(angle) * speed, 0.0, random.uniform(0.45, 0.8)]
            self.wait = random.uniform(10.0, 40.0)
        x, y, vx, vy, age, life = self.flight
        age += dt
        x += vx * dt
        y += vy * dt
        self.flight = [x, y, vx, vy, age, life]
        self.meteor.fill(0)
        if age >= life:
            self.flight = None
            return
        # fades in quickly and out slowly; the tail gets fainter towards its end
        fade = min(1.0, age / (0.15 * life)) * min(1.0, (life - age) / (0.5 * life))
        for k in range(1, TAIL + 1):
            self.meteor_pal[k] = gfx.scale(0xE8F0FF if k < 3 else 0xB8D0FF, fade * (1.0 - (k - 1) / TAIL) ** 0.8)
        speed = math.sqrt(vx * vx + vy * vy)
        for k in range(TAIL, 0, -1):
            px = int(x - vx / speed * (k - 1))
            py = int(y - vy / speed * (k - 1))
            if 0 <= px < 64 and 0 <= py < self.hills[px]:
                self.meteor[px, py] = k
