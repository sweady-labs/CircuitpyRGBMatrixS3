"""DNA-Helix: a double helix turning around its axis and drifting slowly sideways.

The axis runs across the screen. For every column the two strands are at the angle a and a + 180
degrees around it: their height is the sine, their depth the cosine. The strand in front is drawn
thicker and brighter, the one behind thin and dim, and both are anti-aliased: a strand covers a
little more than one pixel in height, and every pixel gets the brightness of the part it covers.
Base pairs connect the strands every few pixels, each half in the colour of its base (A-T, G-C)
and shaded by depth too. Drawing order makes the 3D: back strand, base pairs, front strand.
"""
import math
import random

import bitmaptools

from app import gfx

FPS = 20
PREVIEW_AT = 2.0

PITCH = 42.0  # pixels per full turn (about 10 base pairs, like the real thing)
SPACING = 4  # pixels between base pairs
SPIN = 1.5  # radians per second around the axis
DRIFT = 3.0  # pixels per second to the right
PAIRS = 97  # length of the base sequence; a prime, so it never lines up with the turns
LEVELS = 12  # brightness steps of a strand
RUNG_LEVELS = 4
# strand colours (one pair per theme) and the bases: A red, T amber, G green, C blue
THEMES = ((0x4FD8FF, 0xFF5FD0), (0xFFB347, 0x7C83FF), (0x6BFF9E, 0xC77DFF))
BASES = (0xFF4D4D, 0xFFC233, 0x4DE36B, 0x3FA9FF)
PAIR = (1, 0, 3, 2)  # A-T, G-C
THEME_SECONDS = 50
BLEND_SECONDS = 5


class Scene:
    def __init__(self, group, settings):
        self.strand_first = (1, 1 + LEVELS)  # palette start of strand A and strand B
        self.rung_first = 1 + 2 * LEVELS
        self.bitmap, self.pal = gfx.canvas(group, [0] * (self.rung_first + len(BASES) * RUNG_LEVELS))
        for base, color in enumerate(BASES):
            for level in range(RUNG_LEVELS):
                # dimmer than the strands, so the backbones stay in front
                self.pal[self.rung_first + base * RUNG_LEVELS + level] = gfx.scale(color, 0.22 + 0.45 * level / 3)
        self.theme = 0
        self.theme_time = 0.0
        self.paint_strands(THEMES[0])
        # with sin and cos of k * x stored, a frame only needs sin and cos of its turn (angle addition)
        k = 2 * math.pi / PITCH
        self.sin_kx = [math.sin(k * x) for x in range(64)]
        self.cos_kx = [math.cos(k * x) for x in range(64)]
        self.k = k
        self.sequence = [random.randrange(4) for _ in range(PAIRS)]  # bases along strand A
        self.t = 0.0
        # angle and drift run on their own and wrap around, so they stay exact for days (floats
        # on the board have 24 bits); the drift wraps after the whole sequence, which nobody sees
        self.turn = 0.0
        self.shift = 0.0

    def paint_strands(self, colors):
        for first, color in zip(self.strand_first, colors):
            for level in range(LEVELS):
                self.pal[first + level] = gfx.scale(color, (level + 1) / LEVELS)

    def brush(self, x, y, depth, first):
        """One strand in column x around height y; depth -1 (behind) ... 1 (in front).

        The strand covers top ... bottom; the pixels at both ends are only partly covered and get
        that share of the brightness. The helix stays between rows 1 and 31, no checks needed."""
        half = 0.55 + 0.5 * max(0.0, depth)  # thicker in front
        shine = (LEVELS - 1) * (0.62 + 0.38 * depth)
        top = y - half
        bottom = y + half
        first_row = int(top)
        last_row = int(bottom)
        bitmap = self.bitmap
        level = int(shine * (first_row + 1 - top) + 0.5)
        if level > 0:
            bitmap[x, first_row] = first + level
        for row in range(first_row + 1, last_row):
            bitmap[x, row] = first + int(shine)
        level = int(shine * (bottom - last_row) + 0.5)
        if level > 0 and last_row > first_row:
            bitmap[x, last_row] = first + level

    def frame(self, dt):
        self.t += dt
        t = self.t
        # the angle at column x is k * x + turn: turning adds to it, drifting to the right takes
        # away k * drift
        self.turn = (self.turn + dt * (SPIN - self.k * DRIFT)) % (2 * math.pi)
        self.shift = (self.shift + dt * DRIFT) % (SPACING * PAIRS)
        shift = self.shift
        # the axis bobs and tilts a little, the helix breathes
        cy = 16.0 + 1.2 * math.sin(t * 0.31)
        tilt = 0.06 * math.sin(t * 0.13)
        radius = 10.0 + 0.8 * math.sin(t * 0.21)
        sin_c, cos_c = math.sin(self.turn), math.cos(self.turn)

        bitmap = self.bitmap
        bitmap.fill(0)
        a_first, b_first = self.strand_first
        heights = []
        fronts = []
        for x in range(64):
            s = self.sin_kx[x] * cos_c + self.cos_kx[x] * sin_c  # sin(k * x + turn)
            depth = self.cos_kx[x] * cos_c - self.sin_kx[x] * sin_c  # cos(k * x + turn)
            axis = cy + tilt * (x - 32)
            ya = axis + radius * s
            yb = axis - radius * s
            heights.append((ya, yb, depth, axis))
            # the strand behind now, the one in front after the base pairs
            if depth >= 0.0:
                self.brush(x, yb, -depth, b_first)
                fronts.append((ya, depth, a_first))
            else:
                self.brush(x, ya, depth, a_first)
                fronts.append((yb, -depth, b_first))

        # base pairs: every SPACING pixels of the helix, moving along with the drift
        j = int(-shift // SPACING)
        while True:
            x = int(j * SPACING + shift + 0.5)
            if x >= 64:
                break
            if x >= 0:
                ya, yb, depth, axis = heights[x]
                if abs(ya - yb) > 2.0:
                    base = self.sequence[j % PAIRS]
                    # each half is as bright as the strand it hangs on is near
                    near_a = int((RUNG_LEVELS - 1) * (0.5 + 0.5 * depth) + 0.5)
                    near_b = RUNG_LEVELS - 1 - near_a
                    rung = self.rung_first
                    bitmaptools.draw_line(bitmap, x, int(ya), x, int(axis), rung + base * RUNG_LEVELS + near_a)
                    bitmaptools.draw_line(bitmap, x, int(axis), x, int(yb), rung + PAIR[base] * RUNG_LEVELS + near_b)
            j += 1

        for x in range(64):
            y, depth, first = fronts[x]
            self.brush(x, y, depth, first)

        self.change_theme(dt)

    def change_theme(self, dt):
        self.theme_time += dt
        if self.theme_time < THEME_SECONDS:
            return
        blend = (self.theme_time - THEME_SECONDS) / BLEND_SECONDS
        old = THEMES[self.theme]
        new = THEMES[(self.theme + 1) % len(THEMES)]
        if blend >= 1.0:
            self.theme = (self.theme + 1) % len(THEMES)
            self.theme_time = 0.0
            self.paint_strands(new)
        else:
            self.paint_strands([gfx.mix(a, b, blend) for a, b in zip(old, new)])
