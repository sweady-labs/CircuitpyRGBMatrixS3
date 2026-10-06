"""Christbaumkugeln: glass baubles swinging on threads below a fir branch with fairy lights.

The baubles are drawn once at the start as shaded spheres (light from the upper left, a white
highlight, a soft reflection at the lower rim) with their pattern, cap and loop. Each sphere is
drawn twice, the second time half a pixel further right, so the swing moves in half pixel steps.
Two baubles slowly turn on their thread: their stripes follow the longitude of each pixel, and
turning only moves the colors along the palette. Now and then a gust makes them all swing wider.
"""
import math
import random

import bitmaptools
import displayio

from app import gfx

FPS = 25
PREVIEW_AT = 2.0
SHADES = 4  # shadow, body, lit, gleam
TURN_STEPS = 24  # longitude steps of a turning bauble
LIGHT = (-0.5, -0.62, 0.6)
GOLD = (0xFFE8A0, 0xD8A030, 0x7A4A10)  # cap and loop: light, mid, dark
PIVOT_Y = 4  # threads start in the branch

# (radius, x of the thread on the branch, thread length, body color, pattern, accent color)
BAUBLES = (
    (4, 7, 12, 0x2058F0, "bands", 0xE8F0FF),
    (5, 19, 6, 0xD81028, "zigzag", 0xFFC838),
    (6, 33, 9, 0xF0B020, "turn", 0xD01020),
    (5, 47, 11, 0x14A040, "dots", 0xFFE070),
    (4, 58, 7, 0xA828D8, "turn", 0xFFFFFF),
)

GLINT = (
    (".....", ".....", "..a..", ".....", "....."),
    (".....", "..b..", ".bab.", "..b..", "....."),
    ("..b..", "..a..", "baaab", "..a..", "..b.."),
)
GLINT_SEQUENCE = (0, 1, 2, 2, 1, 0)
GLINT_STEP = 0.07

# lights far behind, out of focus: (x, y, color); each gets a faint halo
FAR = ((3, 27, 0xFFB050), (12, 12, 0xFFD890), (26, 22, 0xFF9070), (41, 13, 0xFFC870), (53, 21, 0x90B0FF),
       (62, 13, 0xFFB050), (34, 31, 0xFFD890), (20, 30, 0x90B0FF), (46, 28, 0xFF9070), (57, 30, 0xFFC870))


def normalized(x, y, z):
    n = math.sqrt(x * x + y * y + z * z)
    return x / n, y / n, z / n


class Bauble:
    """A glass bauble: two half-pixel frames in one sprite sheet, with its own palette."""

    def __init__(self, group, radius, anchor, length, color, pattern, accent):
        self.radius = radius
        self.anchor = anchor
        self.length = length
        self.phase = random.uniform(0, 6.3)
        self.period = 1.3 * math.sqrt(length)  # longer threads swing slower, like a pendulum
        self.turning = pattern == "turn"
        self.turn = random.random()
        self.turn_step = -1
        self.body = [self.shade(color, s) for s in range(SHADES)]
        self.stripe = [self.shade(accent, s) for s in range(SHADES)]
        # palette: 0 clear, body shades (pattern x shade, or shade x longitude when turning), extras
        count = SHADES * (TURN_STEPS if self.turning else 2)
        self.highlight = 1 + count
        self.rim = self.highlight + 1
        self.cap = self.rim + 1
        colors = [0] * (self.cap + 3)
        if not self.turning:
            colors[1:1 + 2 * SHADES] = self.body + self.stripe
        colors[self.highlight] = 0xFFFFFF
        colors[self.rim] = gfx.mix(color, 0xFFFFFF, 0.5)
        colors[self.cap:self.cap + 3] = GOLD
        self.pal = gfx.Pal(colors, transparent=(0,))

        self.mid = radius + 1  # x of the loop in the sprite
        size = 2 * radius + 3
        height = 2 * radius + 7  # loop and cap above the sphere
        sheet = displayio.Bitmap(size * 2, height, len(colors))
        self.shine = []  # highlight pixels, for the glints
        for frame in range(2):
            self.draw(sheet, frame * size, self.mid + 0.5 + 0.5 * frame, pattern)
        self.grid = displayio.TileGrid(sheet, pixel_shader=self.pal.palette, tile_width=size, tile_height=height)
        group.append(self.grid)
        self.loop = (anchor, PIVOT_Y + length)

    @staticmethod
    def shade(color, s):
        if s == 0:
            return gfx.mix(gfx.scale(color, 0.5), 0x200838, 0.2)  # shadows go a bit violet
        if s == 3:
            return gfx.mix(color, 0xFFFFFF, 0.38)  # the glass gleams round the highlight
        return gfx.scale(color, 0.78) if s == 1 else color

    def draw(self, sheet, left, cx, pattern):
        r = self.radius
        cy = r + 5.5  # sphere centre; rows 0-4 hold loop and cap
        lx, ly, lz = normalized(*LIGHT)
        hx, hy, hz = normalized(lx, ly, lz + 1.0)
        for py in range(5, 2 * r + 7):
            for px in range(2 * r + 3):
                dx, dy = (px + 0.5 - cx) / r, (py + 0.5 - cy) / r
                d2 = dx * dx + dy * dy
                if d2 > 1.0:
                    continue
                dz = math.sqrt(1.0 - d2)
                light = dx * lx + dy * ly + dz * lz
                shade = 3 if light > 0.9 else 2 if light > 0.62 else 1 if light > 0.12 else 0
                if (dx * hx + dy * hy + dz * hz) ** 30 > 0.45:
                    value = self.highlight
                    if left == 0:
                        self.shine.append((px, py))
                elif dx * 0.6 + dy * 0.65 + dz * 0.15 > 0.84:
                    value = self.rim  # the room, mirrored in the lower right edge of the glass
                elif self.turning:
                    lon = math.atan2(dx, dz) / (2 * math.pi)  # -0.25 .. 0.25 on the visible side
                    value = 1 + shade * TURN_STEPS + int((lon + 1.0) * TURN_STEPS) % TURN_STEPS
                else:
                    value = 1 + SHADES * self.pattern(pattern, dx, dy, dz) + shade
                sheet[left + px, py] = value
        # cap with ridges and its dark lower edge, then the loop for the thread
        m = left + self.mid
        half = 1 if r < 5 else 2
        for x in range(m - half, m + half + 1):
            sheet[x, 3] = self.cap + (x - m) % 2
            sheet[x, 4] = self.cap + 2
        sheet[m, 2] = self.cap + 1
        sheet[m - 1, 1] = self.cap + 1
        sheet[m + 1, 1] = self.cap + 1
        sheet[m, 0] = self.cap

    @staticmethod
    def pattern(pattern, dx, dy, dz):
        """0 where the body color shows, 1 for the accent color, by the point on the sphere."""
        if pattern == "bands":
            return 1 if abs(dy) < 0.15 or 0.42 < abs(dy) < 0.55 else 0
        lon = math.atan2(dx, dz)
        if pattern == "zigzag":
            zig = abs((lon * 4 / math.pi) % 2.0 - 1.0) * 0.64 - 0.32  # -0.32 .. 0.32
            return 1 if abs(dy - zig) < 0.2 else 0
        if pattern == "dots":
            ring = abs(dy) < 0.2 and (lon * 5 / math.pi) % 2.0 < 0.9
            top = abs(dy + 0.58) < 0.13 and (lon * 4 / math.pi + 0.5) % 2.0 < 0.8
            return 1 if ring or top else 0
        return 0

    def turn_colors(self, dt):
        """A turning bauble: its stripes move one longitude step after the other."""
        self.turn = (self.turn + dt / 16.0) % 1.0
        step = int(self.turn * TURN_STEPS)
        if step == self.turn_step:
            return
        self.turn_step = step
        pal = self.pal
        for p in range(TURN_STEPS):
            colors = self.stripe if (p + step) % 4 == 0 else self.body  # six stripes all round
            for s in range(SHADES):
                pal[1 + s * TURN_STEPS + p] = colors[s]

    def swing(self, t, amplitude):
        """Hang the bauble at its swing angle; the loop ends up at self.loop."""
        angle = amplitude * math.sin(t * 2 * math.pi / self.period + self.phase)
        x = self.anchor + 0.5 + self.length * math.sin(angle)  # 0.5: the thread starts in a pixel centre
        y = PIVOT_Y + int(self.length * math.cos(angle) + 0.5)
        h = int(x * 2 + 0.5)  # nearest half pixel
        if h & 1:
            self.grid[0] = 0  # centre in the middle of a pixel
            self.grid.x = (h - 1) // 2 - self.mid
        else:
            self.grid[0] = 1  # centre between two pixels
            self.grid.x = h // 2 - self.mid - 1
        self.grid.y = y
        self.loop = (self.grid.x + self.mid, y)


class Scene:
    def __init__(self, group, settings):
        self.far_lights(group)
        self.threads = displayio.Bitmap(64, 32, 2)
        self.thread_pal = gfx.Pal((0, 0x8A6A30), transparent=(0,))
        group.append(displayio.TileGrid(self.threads, pixel_shader=self.thread_pal.palette))
        self.baubles = [Bauble(group, *spec) for spec in BAUBLES]
        self.branch(group)
        sheet, w, h = gfx.sprite_sheet(GLINT, {".": 0, "a": 1, "b": 2})
        self.glint_pal = gfx.Pal((0, 0xFFFFFF, 0xFFE0A0), transparent=(0,))
        self.glint = displayio.TileGrid(sheet, pixel_shader=self.glint_pal.palette, tile_width=w, tile_height=h)
        self.glint.hidden = True
        group.append(self.glint)
        self.glint_time = 1.2
        self.glint_on = None  # (bauble, x, y in its sprite) while a glint shows
        self.lines = [None] * len(self.baubles)
        self.t = 0.0
        self.frames = 0
        self.gust = 0.4
        self.next_gust = random.uniform(15, 30)

    def far_lights(self, group):
        """Lights far behind, out of focus: a dim point with a faint halo, glowing up and down."""
        self.far_pal = gfx.Pal([0] * (1 + 2 * len(FAR)))
        bitmap = displayio.Bitmap(64, 32, len(self.far_pal))
        for i, (x, y, color) in enumerate(FAR):
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if 0 <= x + dx < 64 and 0 <= y + dy < 32:
                    bitmap[x + dx, y + dy] = 2 + 2 * i
            bitmap[x, y] = 1 + 2 * i
        group.append(displayio.TileGrid(bitmap, pixel_shader=self.far_pal.palette))
        self.far_phase = [random.uniform(0, 6.3) for _ in FAR]

    def branch(self, group):
        """Fir branch across the top: needles in three greens around a hidden twig, fairy lights."""
        colors = [0, 0x5A3418, 0x08301A, 0x126028, 0x30A044, 0x70D478, 0xD0E4F8] + [0xFFC060] * 6 + [0x805020] * 6
        self.branch_pal = gfx.Pal(colors, transparent=(0,))
        bitmap = displayio.Bitmap(64, 11, len(colors))
        twig = [int(2.8 + 1.0 * math.sin(x * 0.085 + 0.7)) for x in range(64)]
        for x in range(64):
            s = twig[x]
            n = (x * 37 + 11) % 7  # a little hash, so the needles end unevenly
            up = 1 + (n % 3 == 0)
            down = 2 + (n < 3) + int(1.2 + 1.2 * math.sin(x * 0.31))
            for y in range(max(0, s - up), min(11, s + down + 1)):
                if y < s:
                    # above the twig the needles point up and forward, lit from above
                    stroke = (x + y) % 3 == 0
                    value = (5 if stroke else 4) if y == s - up else (4 if stroke else 3)
                elif y > s:
                    # below they hang down and forward, in the shade
                    stroke = (x - y) % 3 == 0
                    value = (4 if stroke else 3) if y == s + down else (3 if stroke else 2)
                else:
                    value = 1 if n < 3 else 2  # the twig peeks out here and there
                bitmap[x, y] = value
            if n == 4 and s >= 2:
                bitmap[x, s - 2] = 6  # a bit of frost on the tips
        self.fairy = []
        for i, x in enumerate((4, 14, 26, 40, 52, 61)):
            # a bulb hanging below the needles, with a faint glow round it
            y = twig[x] + 4
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                bitmap[x + dx, y + dy] = 13 + i
            bitmap[x, y] = 7 + i
            self.fairy.append(random.uniform(0, 6.3))
        group.append(displayio.TileGrid(bitmap, pixel_shader=self.branch_pal.palette))

    def frame(self, dt):
        self.t += dt
        t = self.t
        # gusts: now and then the baubles swing wider and settle again over half a minute
        self.next_gust -= dt
        if self.next_gust <= 0:
            self.next_gust = random.uniform(25, 50)
            self.gust = 1.0
        self.gust = max(0.0, self.gust - dt * 0.035)
        amplitude = 0.06 + 0.16 * self.gust * self.gust
        for i, bauble in enumerate(self.baubles):
            bauble.swing(t, amplitude)
            if bauble.turning:
                bauble.turn_colors(dt)
            line = (bauble.anchor, PIVOT_Y, bauble.loop[0], bauble.loop[1] - 1)
            if line != self.lines[i]:
                old = self.lines[i]
                if old:
                    bitmaptools.draw_line(self.threads, old[0], old[1], old[2], old[3], 0)
                bitmaptools.draw_line(self.threads, line[0], line[1], line[2], line[3], 1)
                self.lines[i] = line
        self.lights(dt)
        self.sparkle(dt)

    def lights(self, dt):
        # fairy lights flicker softly, the far lights glow up and down slowly
        for i in range(len(self.fairy)):
            self.fairy[i] += dt * (1.3 + 0.2 * i)
            glow = 0.6 + 0.4 * math.sin(self.fairy[i]) ** 2
            self.branch_pal[7 + i] = gfx.mix(0xFF9020, 0xFFF0C0, glow)
            self.branch_pal[13 + i] = gfx.scale(0x9A5A18, glow)
        self.frames += 1
        if self.frames % 3 == 0:  # so slow that every third frame is enough
            for i, (x, y, color) in enumerate(FAR):
                level = 0.5 + 0.5 * math.sin(self.t * 0.5 + self.far_phase[i])
                self.far_pal[1 + 2 * i] = gfx.scale(color, 0.25 + 0.4 * level)
                self.far_pal[2 + 2 * i] = gfx.scale(color, 0.1 + 0.16 * level)

    def sparkle(self, dt):
        """Now and then a glint flashes on the highlight of a bauble and travels with it."""
        self.glint_time -= dt
        if self.glint_time > 0:
            return
        step = int(-self.glint_time / GLINT_STEP)
        if step >= len(GLINT_SEQUENCE):
            self.glint.hidden = True
            self.glint_on = None
            self.glint_time = random.uniform(0.8, 2.5)
            return
        if self.glint_on is None:
            bauble = random.choice(self.baubles)
            x, y = random.choice(bauble.shine)
            self.glint_on = (bauble, x, y)
            self.glint.hidden = False
        bauble, x, y = self.glint_on
        self.glint.x = bauble.grid.x + x - 2
        self.glint.y = bauble.grid.y + y - 2
        self.glint[0] = GLINT_SEQUENCE[step]
