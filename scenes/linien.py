"""Linienspiel: line art in two acts that take turns, ribbons and an oscilloscope figure.

Ribbons (like the old Mystify screensaver): two four-cornered shapes whose corners bounce off the
edges. Every few hundredths of a second a copy of each shape is kept, and the copies are drawn
dimmer the older they are, so each shape pulls a fading ribbon behind it.

Figure: a Lissajous curve, x = sin(a s + phase), y = sin(b s). Read as a curve in space that is
seen from the side, cos(a s + phase) is its depth: parts in front are drawn brighter, parts
behind dimmer, and as the phase runs the figure seems to turn. Now and then it changes to another
ratio a:b. The colours of both acts wander slowly round the colour wheel.
"""
import math
import random

import bitmaptools

from app import gfx

FPS = 25
PREVIEW_AT = 4.0

ACT_SECONDS = 45  # how long an act lasts
FADE_SECONDS = 1.5  # fading out and in between acts and figures
LEVELS = 8  # brightness steps of every colour

SHAPES = 2
CORNERS = 4
ECHOES = 6  # copies kept per shape
ECHO_SECONDS = 0.12  # time between two copies

POINTS = 72  # segments of the figure
RATIOS = ((1, 2), (3, 2), (3, 4), (2, 3), (5, 4), (1, 3), (4, 3), (5, 6))
FIGURE_SECONDS = 15
BANDS = 4  # colour bands along the figure


class Ribbons:
    def __init__(self):
        self.corners = []
        for _ in range(SHAPES * CORNERS):
            speed = random.uniform(10.0, 22.0)
            angle = random.uniform(0, 2 * math.pi)
            self.corners.append([random.uniform(0, 63), random.uniform(0, 31),
                                 math.cos(angle) * speed, math.sin(angle) * speed])
        self.echoes = []  # oldest first, each a list of (x, y) of all corners
        self.wait = 0.0

    def draw(self, bitmap, dt):
        for corner in self.corners:
            corner[0] += corner[2] * dt
            corner[1] += corner[3] * dt
            # bounce off the edges, each time with a slightly different speed, so the shapes
            # never fall into a repeating path
            if not 0.0 <= corner[0] <= 63.0:
                corner[0] = min(63.0, max(0.0, corner[0]))
                corner[2] = -corner[2] * random.uniform(0.9, 1.1)
            if not 0.0 <= corner[1] <= 31.0:
                corner[1] = min(31.0, max(0.0, corner[1]))
                corner[3] = -corner[3] * random.uniform(0.9, 1.1)
            speed = abs(corner[2]) + abs(corner[3])
            if speed > 34.0 or speed < 14.0:  # keep the speed in a calm range
                corner[2] *= 24.0 / speed
                corner[3] *= 24.0 / speed
        self.wait -= dt
        if self.wait <= 0.0:
            self.wait = ECHO_SECONDS
            self.echoes.append([(int(c[0]), int(c[1])) for c in self.corners])
            if len(self.echoes) > ECHOES:
                self.echoes.pop(0)
        # oldest copy first and dimmest, so the newer ones lie on top
        start = LEVELS - len(self.echoes)
        for age, points in enumerate(self.echoes):
            for shape in range(SHAPES):
                value = 1 + shape * LEVELS + start + age
                ring = points[shape * CORNERS:(shape + 1) * CORNERS]
                x0, y0 = ring[-1]
                for x1, y1 in ring:
                    bitmaptools.draw_line(bitmap, x0, y0, x1, y1, value)
                    x0, y0 = x1, y1

    def colors(self, hue, fade):
        colors = []
        for shape in range(SHAPES):
            color = gfx.hsv(hue + shape * 0.35, 0.85, 1.0)
            for level in range(LEVELS):
                colors.append(gfx.scale(color, fade * ((level + 1) / LEVELS) ** 1.4))
        return colors


class Figure:
    def __init__(self):
        self.ratio = random.choice(RATIOS)
        self.phase = 0.0

    def draw(self, bitmap, dt):
        self.phase += dt * 0.45
        a, b = self.ratio
        first = 1 + SHAPES * LEVELS
        step = 2 * math.pi / POINTS
        x0 = y0 = None
        for i in range(POINTS + 1):
            s = i * step
            u = a * s + self.phase
            x = int(32.0 + 29.0 * math.sin(u) + 0.5)
            y = int(16.0 + 14.0 * math.sin(b * s) + 0.5)
            if x0 is not None:
                # cos(u) is the depth: in front bright, behind dim
                level = int((LEVELS - 1) * (0.55 + 0.45 * math.cos(u)) + 0.5)
                band = i * BANDS // (POINTS + 1)
                bitmaptools.draw_line(bitmap, x0, y0, x, y, first + band * LEVELS + level)
            x0, y0 = x, y

    def colors(self, hue, fade):
        colors = []
        for band in range(BANDS):
            # the bands go up and down in hue, so the figure has no seam where it closes
            color = gfx.hsv(hue + 0.07 * min(band, BANDS - band), 0.8, 1.0)
            for level in range(LEVELS):
                colors.append(gfx.scale(color, fade * ((level + 1) / LEVELS) ** 1.2))
        return colors


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * (1 + (SHAPES + BANDS) * LEVELS))
        self.act = Ribbons()
        self.act_time = 0.0
        self.figure_time = 0.0
        self.hue = random.random()
        self.frames = 0

    def fade(self):
        """Brightness: up at the start of an act, down at its end, and between two figures."""
        fade = min(1.0, self.act_time / FADE_SECONDS, (ACT_SECONDS - self.act_time) / FADE_SECONDS)
        if isinstance(self.act, Figure):
            left = FIGURE_SECONDS - self.figure_time
            fade = min(fade, self.figure_time / FADE_SECONDS, left / FADE_SECONDS)
        return max(0.0, fade)

    def frame(self, dt):
        self.act_time += dt
        self.figure_time += dt
        if self.act_time >= ACT_SECONDS:
            self.act = Figure() if isinstance(self.act, Ribbons) else Ribbons()
            self.act_time = 0.0
            self.figure_time = 0.0
        if isinstance(self.act, Figure) and self.figure_time >= FIGURE_SECONDS:
            self.act.ratio = random.choice([r for r in RATIOS if r != self.act.ratio])
            self.figure_time = 0.0

        self.bitmap.fill(0)
        self.act.draw(self.bitmap, dt)

        # colours: the hue wanders; the palette is set every other frame, that is plenty
        self.hue = (self.hue + dt * 0.02) % 1.0
        self.frames += 1
        if self.frames % 2:
            fade = self.fade()
            colors = self.act.colors(self.hue, fade)
            first = 1 if isinstance(self.act, Ribbons) else 1 + SHAPES * LEVELS
            for i, color in enumerate(colors):
                self.pal[first + i] = color
