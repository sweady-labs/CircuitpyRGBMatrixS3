"""Zuckerstange: two crossed candy canes tied with a bow, their stripes twisting round, in falling snow.

Every pixel of a cane is drawn once, at the start: its palette index says how bright the cane is
there (round shading) and where it lies on the helix of the stripes. To make a cane turn, only its
palette changes: the stripe colors move one phase step further. So the twist costs a few palette
colors per frame and no pixels at all.
"""
import math
import random

import displayio
import vectorio

from app import gfx

FPS = 20
PREVIEW_AT = 2.0
SHADES = 4  # dark edge, shadow, body, highlight
PHASES = 16  # phase steps per stripe period

# stripe themes: (end of band within one period, color); the bands cover 0..1
RED, WHITE, GREEN = 0xE8102C, 0xF4ECEA, 0x10C048
CLASSIC = ((0.56, RED), (1.0, WHITE))
MINT = ((0.34, GREEN), (0.5, WHITE), (0.72, RED), (1.0, WHITE))
# shadows of each stripe color: (dark edge, shadow, body, highlight)
LOOK = {
    RED: (0x5C0418, 0x9C0A24, RED, 0xFF7088),
    WHITE: (0x5A6290, 0xA8B0D4, WHITE, 0xFFFFFF),
    GREEN: (0x044A20, 0x0A8034, GREEN, 0x90FFB0),
}

BOW = (
    ".oo.........oo.",
    "oGgo.......ogGo",
    "oGggo.....oggGo",
    "oGgggokkkogggGo",
    "oggggkKKkkggggo",
    "odgggokkkogggdo",
    "oddgoogdgoogddo",
    ".oooogddgoooo..",
    "....ogdodgo....",
    "...ogdo.odgo...",
    "...ooo...ooo...",
)
BOW_COLORS = (0, 0x18A848, 0x86F4A4, 0x0A6A2C, 0x02240E, 0xFFB820, 0xFFF0A0)  # 0 transparent
BOW_KEYS = {".": 0, "g": 1, "G": 2, "d": 3, "o": 4, "k": 5, "K": 6}
# a glint on the sugar: grows from a dot to a little star and back
GLINT = (
    (".......", ".......", ".......", "...a...", ".......", ".......", "......."),
    (".......", ".......", "...b...", "..bab..", "...b...", ".......", "......."),
    (".......", "...b...", "...a...", ".baaab.", "...a...", "...b...", "......."),
    ("...b...", "...a...", "..bab..", "baaaaab", "..bab..", "...a...", "...b..."),
)
GLINT_COLORS = (0, 0xFFFFFF, 0xFFD878)
GLINT_SEQUENCE = (0, 1, 2, 3, 3, 2, 1, 0)  # frames of one glint, GLINT_STEP seconds each
GLINT_STEP = 0.08
FLAKES = (0xFFFFFF, 0x8E9CBC)


def shade_of(v):
    """Shade step for the position across the cane: v = 1 on the lit side, -1 on the dark side."""
    if v > 0.55:
        return 2
    if v > 0.08:
        return 3
    if v > -0.4:
        return 2
    if v > -0.75:
        return 1
    return 0


class Cane:
    """One candy cane: a straight shaft and a hook, in its own bitmap and palette.

    x, y: lower end of the shaft on the screen; angle: lean in degrees (positive leans right);
    length: shaft length; radius: hook radius; width: thickness; mirror: the hook turns the other
    way. The outer side of the hook is the lit side.
    """

    def __init__(self, group, x, y, angle, length, radius, width, theme, period, speed, mirror=False):
        self.theme = theme
        self.speed = speed
        self.shine = []  # screen positions of the highlight, for the glints
        self.phase = random.random()
        self.step = -1
        self.t = random.uniform(0, 30)
        self.pal = gfx.Pal([0] * (1 + SHADES * PHASES), transparent=(0,))

        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        half = width / 2
        # bounding box on the screen: the corners of the upright cane, turned
        top_y = -(length + radius + half + 1)
        right_x = 2 * radius + half + 1
        corners = [(-half - 1, half + 1), (right_x, half + 1), (-half - 1, top_y), (right_x, top_y)]
        if mirror:
            corners = [(-cx, cy) for cx, cy in corners]
        xs = [x + cx * ca - cy * sa for cx, cy in corners]
        ys = [y + cx * sa + cy * ca for cx, cy in corners]
        left, top = max(0, int(min(xs))), max(0, int(min(ys)))
        w, h = min(64, int(max(xs)) + 2) - left, min(32, int(max(ys)) + 2) - top
        bitmap = displayio.Bitmap(w, h, 1 + SHADES * PHASES)

        for py in range(h):
            for px in range(w):
                # screen -> cane coordinates: shaft from (0, 0) up to (0, -length), hook to the right
                dx, dy = left + px + 0.5 - x, top + py + 0.5 - y
                qx = dx * ca + dy * sa
                qy = -dx * sa + dy * ca
                if mirror:
                    qx = -qx
                hit = self.locate(qx, qy, length, radius, half)
                if hit is None:
                    continue
                u, v = hit
                # helix: along the cane plus a slant across it, so the stripes run diagonally
                phase = u / period + v * 0.22
                step = int((phase - math.floor(phase)) * PHASES) % PHASES
                shade = shade_of(v)
                bitmap[px, py] = 1 + shade * PHASES + step
                if shade == 3:
                    self.shine.append((left + px, top + py))
        group.append(displayio.TileGrid(bitmap, pixel_shader=self.pal.palette, x=left, y=top))

    @staticmethod
    def locate(qx, qy, length, radius, half):
        """(u along the cane, v across it from -1 to 1) of the nearest centre line point, or None."""
        if qy > 0:
            best = (math.sqrt(qx * qx + qy * qy), 0.0, -qx / half)  # round lower end
        elif qy >= -length:
            best = (abs(qx), -qy, -qx / half)
        else:
            best = None
        if qy > -length + radius + half:
            # well below the hook: only the shaft can be here (most pixels, so skip the hook maths)
            return None if best[0] > half else (best[1], max(-1.0, min(1.0, best[2])))
        # hook: around (radius, -length), from the shaft over the top and a little down again
        cx, cy = qx - radius, qy + length
        r = math.sqrt(cx * cx + cy * cy)
        angle = math.atan2(-cy, cx)  # pi at the shaft, pi/2 on top, 0 on the far side
        end = -0.5
        if angle >= end:
            dist = abs(r - radius)
            if best is None or dist < best[0]:
                best = (dist, length + radius * (math.pi - angle), (r - radius) / half)
        elif angle > -math.pi / 2:
            # round tip of the hook
            ex, ey = radius + radius * math.cos(end), -length - radius * math.sin(end)
            dist = math.sqrt((qx - ex) ** 2 + (qy - ey) ** 2)
            if best is None or dist < best[0]:
                best = (dist, length + radius * (math.pi - end), (r - radius) / half)
        if best is None or best[0] > half:
            return None
        return best[1], max(-1.0, min(1.0, best[2]))

    def frame(self, dt):
        # the twist speeds up and slows down over half a minute, so it never looks mechanical
        self.t += dt
        self.phase = (self.phase + dt * self.speed * (0.65 + 0.35 * math.sin(self.t * 0.21))) % 1.0
        step = int(self.phase * PHASES)
        if step == self.step:
            return  # nothing to change until the stripes have moved a whole step
        self.step = step
        pal = self.pal
        for p in range(PHASES):
            pos = ((p + 0.5) / PHASES - self.phase) % 1.0
            band = 0
            while self.theme[band][0] <= pos:
                band += 1
            look = LOOK[self.theme[band][1]]
            for s in range(SHADES):
                pal[1 + s * PHASES + p] = look[s]


class Scene:
    def __init__(self, group, settings):
        self.flake_pal = gfx.Pal(FLAKES)
        self.flakes = []
        for _ in range(14):
            self.flakes.append(self.flake(group, 1, 0.55))
        self.canes = [
            Cane(group, 61, 33, -64, 50, 5, 4.2, MINT, 7.0, -0.3, mirror=True),
            Cane(group, 3, 33, 64, 50, 5, 4.2, CLASSIC, 7.0, 0.36),
        ]
        bow = gfx.art_bitmap(BOW, BOW_KEYS, len(BOW_COLORS))
        self.bow_pal = gfx.Pal(BOW_COLORS, transparent=(0,))
        group.append(displayio.TileGrid(bow, pixel_shader=self.bow_pal.palette, x=25, y=13))
        sheet, w, h = gfx.sprite_sheet(GLINT, {".": 0, "a": 1, "b": 2})
        self.glint_pal = gfx.Pal(GLINT_COLORS, transparent=(0,))
        self.glint = displayio.TileGrid(sheet, pixel_shader=self.glint_pal.palette, tile_width=w, tile_height=h)
        self.glint.hidden = True
        group.append(self.glint)
        self.shine = self.canes[0].shine + self.canes[1].shine
        self.glint_time = 1.0  # until the next glint; negative while one is shown
        for _ in range(8):
            self.flakes.append(self.flake(group, 0, 1.0))
        self.t = 0.0

    def flake(self, group, color, speed):
        shape = vectorio.Rectangle(pixel_shader=self.flake_pal.palette, width=1, height=1,
                                   x=0, y=0, color_index=color)
        group.append(shape)
        return [shape, random.uniform(0, 64), random.uniform(-2, 30), random.uniform(3.0, 5.5) * speed,
                random.uniform(0, 6.3)]

    def frame(self, dt):
        self.t += dt
        for cane in self.canes:
            cane.frame(dt)
        self.sparkle(dt)
        # snow: each flake sways on its own, a slow gust moves them all a little
        wind = 2.5 * math.sin(self.t * 0.13)
        for f in self.flakes:
            f[2] += f[3] * dt
            f[4] += dt
            if f[2] >= 32:
                f[2] = -1.0
                f[1] = random.uniform(0, 64)
            f[0].x = int(f[1] + wind + 1.5 * math.sin(f[4] * 0.9))
            f[0].y = int(f[2])

    def sparkle(self, dt):
        """Now and then a glint flashes up somewhere on the highlight of a cane."""
        self.glint_time -= dt
        if self.glint_time > 0:
            return
        step = int(-self.glint_time / GLINT_STEP)
        if step >= len(GLINT_SEQUENCE):
            self.glint.hidden = True
            self.glint_time = random.uniform(0.6, 2.2)
            return
        if self.glint.hidden:
            x, y = random.choice(self.shine)
            self.glint.x = x - 3
            self.glint.y = y - 3
            self.glint.hidden = False
        self.glint[0] = GLINT_SEQUENCE[step]
