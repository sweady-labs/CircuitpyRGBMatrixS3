"""Iron Man: the red and gold helmet boots up like the HUD of a suit, then eyes and arc reactor glow.

A scan line builds the helmet as a cyan hologram, a second one turns it into metal, the eyes
flicker on and the arc reactor beside it powers up segment by segment while a power meter fills.
Then it idles, breathing light, with a scan now and then, until it powers down and boots again.
The helmet is shown as two TileGrids of the same pixel art, one tile per row: the scans only
switch rows between the hologram and the metal layer. Everything else is palette animation.
"""
import math
import random

import displayio
import vectorio

from app import gfx

FPS = 25
PREVIEW_AT = 5.5
BUILD, FORGE, EYES, REACTOR, READY = 0.5, 2.3, 3.3, 3.8, 5.5  # seconds into the boot
IDLE = 45.0  # seconds between boot and power down
END = READY + IDLE
RESTART = END + 3.5

# the helmet, left half; the right half is its mirror image
HELMET_HALF = (
    ".....rRRRRR",
    "...rRRRRhhh",
    "..rRRRhhhhh",
    ".rRRRRRhhhh",
    ".rRRRRRRRRR",
    ".rRRRRRRRRR",
    "rRRRRRRGGGG",
    "rRRRRRGGyyy",
    "rRRRRRGGGyy",
    "rRRRRGGGGGG",
    "rRRRRGGGGGG",
    "rRRRmmmmGGG",
    "rRRReeeemGG",
    "rRRGGmeeemG",
    "rRRGGGGmmGG",
    "rRRgGGGGGGG",
    "rRRRgGGGGGG",
    "rRRRGgGGGGG",
    "rRRRGGgGGGG",
    ".rRRGGGgGGG",
    ".rRRRGGGGGG",
    ".rRRRGGGGGG",
    "..rRRGGmmmm",
    "..rRRRgGGGG",
    "...rRRgGGGG",
    "...rrRgGGGG",
    "....rrgGGGG",
    ".....rrrrrr",
)
HELMET = tuple(half + "".join(reversed(half)) for half in HELMET_HALF)
ROWS = len(HELMET)
EMPTY = ROWS  # an empty row below the art, shown where a layer has nothing yet
HELMET_X, HELMET_Y = 3, 2
# red, dark red, red highlight, gold, gold line, gold highlight, eye, dark line around eyes and mouth
KEYS = {".": 0, "R": 1, "r": 2, "h": 3, "G": 4, "g": 5, "y": 6, "e": 7, "m": 8}
METAL = (0, 0xB8101C, 0x6A0810, 0xE8303E, 0xE8A418, 0x6A400A, 0xFFE070, 0xE8FCFF, 0x3A2204)
EYE = 7
HOLOGRAM = 0x38D8FF
# how bright each color shows in the hologram: edges and lines bright, surfaces faint
HOLO_LEVEL = (0, 0.25, 0.6, 0.35, 0.3, 0.7, 0.4, 0.9, 0.9)

REACTOR_X, REACTOR_Y, REACTOR_R = 45, 16, 8
SEGMENTS = 8  # coils; the gaps between them lie on the axes and diagonals, crisp on a pixel grid
CASE, GAP, INNER, CORE, CENTER = 1, 2, 3, 4, 5  # reactor palette, the coils follow
FIRST_SEGMENT = 6
CYAN = 0x60E8FF
COIL = 0x8CEEFF
METER_X, METER_TOP, METER_STEPS = 59, 4, 8  # power meter: 8 bars of 2 rows, 1 row apart


class Scene:
    def __init__(self, group, settings):
        # HUD: corner brackets around the helmet and the power meter
        self.hud, self.hud_pal = gfx.canvas(group, [0, 0, 0] + [0] * METER_STEPS)
        self.draw_hud()

        # the same pixel art twice, as metal and as hologram, one tile per row of pixels
        art = gfx.art_bitmap(HELMET + ("." * len(HELMET[0]),), KEYS)
        self.metal_pal = gfx.Pal(METAL, transparent=(0,))
        self.holo_pal = gfx.Pal([gfx.scale(HOLOGRAM, level) for level in HOLO_LEVEL], transparent=(0,))
        self.metal = displayio.TileGrid(art, pixel_shader=self.metal_pal.palette, width=1, height=ROWS,
                                        tile_width=len(HELMET[0]), tile_height=1, default_tile=EMPTY,
                                        x=HELMET_X, y=HELMET_Y)
        self.holo = displayio.TileGrid(art, pixel_shader=self.holo_pal.palette, width=1, height=ROWS,
                                       tile_width=len(HELMET[0]), tile_height=1, default_tile=EMPTY,
                                       x=HELMET_X, y=HELMET_Y)
        group.append(self.metal)
        group.append(self.holo)

        self.reactor_pal = gfx.Pal([0] * (FIRST_SEGMENT + SEGMENTS), transparent=(0,))
        group.append(displayio.TileGrid(self.reactor_bitmap(), pixel_shader=self.reactor_pal.palette,
                                        x=REACTOR_X - REACTOR_R, y=REACTOR_Y - REACTOR_R))

        self.scan_pal = gfx.Pal([0, HOLOGRAM])
        self.scan = vectorio.Rectangle(pixel_shader=self.scan_pal.palette, width=24, height=1, x=HELMET_X - 1,
                                       y=-5, color_index=1)
        group.append(self.scan)
        self.restart()

    def restart(self):
        self.time = 0.0
        self.built = 0  # hologram rows shown so far
        self.forged = 0  # rows already turned into metal
        self.scan_at = READY + 6.0  # next scan while idling
        self.metal_pal.set_all(METAL)  # the power down dimmed it
        for y in range(ROWS):
            self.holo[0, y] = EMPTY
            self.metal[0, y] = EMPTY

    # --- Pictures ---------------------------------------------------------------------

    def draw_hud(self):
        b = self.hud
        # brackets in the four corners of the helmet's box
        left, top, right, bottom = HELMET_X - 2, 0, HELMET_X + 23, 31
        for x, y, dx, dy in ((left, top, 1, 1), (right, top, -1, 1), (left, bottom, 1, -1), (right, bottom, -1, -1)):
            for i in range(4):
                b[x + dx * i, y] = 1
                b[x, y + dy * i] = 1
        # power meter: dim dots on both sides, bars inside, the bottom bar has the first palette entry
        for step in range(METER_STEPS):
            y = METER_TOP + 3 * step
            b[METER_X - 1, y] = 2
            b[METER_X + 3, y] = 2
            for x in range(METER_X, METER_X + 3):
                b[x, y] = 3 + (METER_STEPS - 1 - step)
                b[x, y + 1] = 3 + (METER_STEPS - 1 - step)

    def reactor_bitmap(self):
        """Arc reactor: bright core, a dark inner ring, eight glowing coils, the metal case."""
        size = 2 * REACTOR_R + 1
        bitmap = displayio.Bitmap(size, size, FIRST_SEGMENT + SEGMENTS)
        for y in range(size):
            for x in range(size):
                dx, dy = x - REACTOR_R, y - REACTOR_R
                d = math.sqrt(dx * dx + dy * dy)
                if d > REACTOR_R + 0.3:
                    continue
                if d > REACTOR_R - 1.2:
                    value = CASE
                elif d > 4.3:
                    if dx == 0 or dy == 0 or abs(dx) == abs(dy):
                        value = GAP
                    else:
                        angle = (math.atan2(dy, dx) + math.pi / 2) % (2 * math.pi)
                        value = FIRST_SEGMENT + int(angle / (2 * math.pi) * SEGMENTS) % SEGMENTS
                elif d > 3.2:
                    value = INNER
                else:
                    value = CENTER if d < 1.6 else CORE
                bitmap[x, y] = value
        return bitmap

    # --- Frames -----------------------------------------------------------------------

    def frame(self, dt):
        self.time += dt
        if self.time > RESTART:
            self.restart()
        t = self.time
        fade = 1.0 if t < END else max(0.0, 1.0 - (t - END) / 2.5)
        self.helmet(t, fade)
        self.eyes(t)
        self.reactor(t)
        self.hud_pal[1] = gfx.scale(CYAN, 0.55 * min(1.0, t / BUILD) * fade)
        self.hud_pal[2] = gfx.scale(CYAN, 0.3 * min(1.0, t / BUILD) * fade)

    def helmet(self, t, fade):
        scan = -5
        if BUILD <= t < FORGE:
            # first scan: the hologram appears row by row
            row = int((t - BUILD) / (FORGE - BUILD) * ROWS)
            while self.built < min(row, ROWS):
                self.holo[0, self.built] = self.built
                self.built += 1
            scan = HELMET_Y + row
            self.scan_pal[1] = HOLOGRAM
        elif FORGE <= t < EYES:
            # second scan: row by row the hologram turns into metal
            while self.built < ROWS:
                self.holo[0, self.built] = self.built
                self.built += 1
            row = int((t - FORGE) / (EYES - FORGE) * ROWS)
            while self.forged < min(row, ROWS):
                self.metal[0, self.forged] = self.forged
                self.holo[0, self.forged] = EMPTY
                self.forged += 1
            scan = HELMET_Y + row
            self.scan_pal[1] = 0xFFE8A0
        elif t >= EYES:
            while self.forged < ROWS:
                self.metal[0, self.forged] = self.forged
                self.holo[0, self.forged] = EMPTY
                self.forged += 1
            if READY < t < END and t > self.scan_at:
                # now and then a scan runs down over the helmet
                scan = HELMET_Y + int((t - self.scan_at) * 22)
                self.scan_pal[1] = HOLOGRAM
                if scan > HELMET_Y + ROWS:
                    self.scan_at = t + random.uniform(6.0, 11.0)
                    scan = -5
            if fade < 1.0:
                for i in range(1, len(METAL)):
                    if i != EYE:
                        self.metal_pal[i] = gfx.scale(METAL[i], fade)
        self.scan.y = scan

    def eyes(self, t):
        """Dim until the eyes flicker on, then breathe; they go out first when powering down."""
        if t < EYES:
            eye = 0.0
        elif t < EYES + 0.8:
            eye = 1.0 if int((t - EYES) * 12) in (0, 2, 3, 6, 7, 8, 9) else 0.1
        elif t < END:
            eye = 0.85 + 0.15 * math.sin(t * 2.2)
        else:
            eye = max(0.0, 1.0 - (t - END) / 0.8)
        self.metal_pal[EYE] = gfx.mix(0x101820, METAL[EYE], eye)

    def reactor(self, t):
        pal = self.reactor_pal
        if t < END:
            # the case appears, then one coil after the other lights up, then the core
            case = min(1.0, max(0.0, (t - REACTOR) / 0.4))
            lit = (t - REACTOR - 0.1) / 0.12  # coils switched on so far
            core = min(1.0, max(0.0, (t - REACTOR - 1.3) / 0.4))
            pulse = 0.9 + 0.1 * math.sin(t * 1.9) if t > READY else 1.0
        else:
            down = (t - END) / 2.0  # power down: coils go out backwards, the core last
            case = max(0.0, 1.0 - down)
            lit = SEGMENTS * (1.0 - down * 1.5)
            core = max(0.0, 1.0 - down)
            pulse = 1.0
        pal[CASE] = gfx.scale(0x4A5262, case)
        pal[GAP] = gfx.scale(0x0C161C, case)
        pal[INNER] = gfx.scale(0x2A3644, case)
        pal[CORE] = gfx.scale(0xC8F8FF, core * pulse)
        pal[CENTER] = gfx.scale(0xFFFFFF, core)
        # while idling a brighter spot runs around the coils
        spot = (t * 1.1) % SEGMENTS
        for i in range(SEGMENTS):
            on = min(1.0, max(0.0, lit - i))
            near = abs(i - spot)
            near = min(near, SEGMENTS - near)
            bright = gfx.mix(COIL, 0xFFFFFF, 0.5 * max(0.0, 1.0 - near)) if READY < t < END else COIL
            pal[FIRST_SEGMENT + i] = gfx.scale(bright, on * pulse)
        # the power meter fills with the coils and wobbles a little when idle
        level = min(1.0, max(0.0, lit / SEGMENTS)) * METER_STEPS
        if READY < t < END:
            level -= 0.6 + 0.6 * math.sin(t * 0.7)
        for step in range(METER_STEPS):
            on = min(1.0, max(0.0, level - step))
            color = gfx.mix(CYAN, 0xFFD040, step / (METER_STEPS - 1))
            self.hud_pal[3 + step] = gfx.scale(color, (0.15 + 0.85 * on) * case)
