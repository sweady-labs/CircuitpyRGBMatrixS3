"""Lebkuchentanz: a gingerbread family dances on the baking tray under a string of lights.

Papa, Mama (icing skirt and bow) and the little one dance to a steady beat: jumping jacks,
waving, kicks, squat jumps and a wave that runs along the row; Mama mirrors Papa. The poses
are made once at the start: head and body with their icing are pixel art, arms and legs are
drawn at the angles of each pose, then the dough gets darker edges. While dancing, only the
sprite frames and positions change. Music notes float up, the lights flash to the beat.
"""
import math
import random

import displayio

from app import gfx

FPS = 25
PREVIEW_AT = 2.0
BEAT = 60 / 104  # seconds per beat
FLOOR = 29  # lowest row of the feet

# poses: (left arm, right arm, left leg, right leg) in degrees from hanging down, outwards
POSES = ((50, 50, 15, 15), (22, 22, 5, 5), (125, 125, 30, 30), (140, 40, 15, 15), (40, 140, 15, 15),
         (95, 95, 75, 10), (95, 95, 10, 75), (95, 95, 42, 42))
STAND, TOGETHER, STAR, WAVE_L, WAVE_R, KICK_L, KICK_R, SQUAT = range(8)
MIRROR = (STAND, TOGETHER, STAR, WAVE_R, WAVE_L, KICK_R, KICK_L, SQUAT)
# dances: one (pose, hop height) per beat, and whether the three start one after another
DANCES = (
    (((TOGETHER, 0), (STAR, 2)) * 4, False),  # jumping jacks
    (((WAVE_L, 0), (WAVE_R, 0)) * 4, False),  # waving
    (((KICK_L, 0), (STAND, 1), (KICK_R, 0), (STAND, 1)) * 2, False),  # kicks
    (((SQUAT, 0), (STAR, 4)) * 4, False),  # squat jumps
    (((STAND, 0), (STAR, 3), (STAND, 0), (STAND, 0)) * 2, True),  # a wave along the row
)

PAPA = (
    "..bbb..",
    ".bbbbb.",
    "bbwbwbb",
    "bbbbbbb",
    "bwbbbwb",
    ".bwwwb.",
    "..bbb..",
    "bbbbbbb",
    "bbbrbbb",
    "bbbbbbb",
    "bbbgbbb",
    "bbbbbbb",
    ".bbbbb.",
)
MAMA = (
    "..bbpPp",
    ".bbbbpp",
    "bbwbwbb",
    "bbbbbbb",
    "bwbbbwb",
    ".bwwwb.",
    "..bbb..",
    "bbbbbbb",
    "bbbrbbb",
    "bbbbbbb",
    "wbwbwbw",
    "bwbwbwb",
    ".bbbbb.",
)
KIND = (
    ".bbb.",
    "bbbbb",
    "bwbwb",
    "bbbbb",
    "wbbbw",
    ".www.",
    "..b..",
    "bbbbb",
    "bbrbb",
    "bbbbb",
    ".bbb.",
)
KEYS = {".": 0, "b": 1, "o": 2, "w": 3, "r": 4, "g": 5, "p": 6, "P": 7}
DOUGH = (0, 0xC87C3A, 0x8A4A1C, 0xFFFFFF, 0xF02040, 0x30D050, 0xFF70A8, 0xFFB0D0)
SPRITE_W, SPRITE_H = 21, 20

NOTES = (
    ("..#....", "..##...", "..#.#..", "..#....", ".##....", "###....", ".#.....", "......."),
    ("..#####", "..#...#", "..#...#", "..#...#", ".##..##", "###.###", ".#...#.", "......."),
)
NOTE_COLORS = (0xFF7090, 0xFFD040, 0x70D0FF, 0x90FF90, 0xD090FF)
BULBS = (0xFF2030, 0x20E040, 0xFFC020, 0x3080FF, 0xFF60C0)


def figure(body, pose, arm, leg, thick, shoulder):
    """Pixel rows of one pose: limbs at their angles, the body on top, darker baked edges."""
    rows = [[0] * SPRITE_W for _ in range(SPRITE_H)]
    width = len(body[0])
    left = (SPRITE_W - width) // 2
    disc = [(dx, dy) for dy in (-2, -1, 0, 1) for dx in (-2, -1, 0, 1)
            if (dx + 0.5) ** 2 + (dy + 0.5) ** 2 <= thick * thick]

    def limb(x0, y0, angle, length, side):
        a = math.radians(angle)
        dx, dy = side * math.sin(a), math.cos(a)
        steps = int(length * 2) + 1
        for k in range(steps + 1):
            x, y = x0 + dx * length * k / steps, y0 + dy * length * k / steps
            for ox, oy in disc:
                px, py = int(x + ox + 0.5), int(y + oy + 0.5)
                if 0 <= px < SPRITE_W and 0 <= py < SPRITE_H:
                    rows[py][px] = KEYS["b"]
        # a line of icing across the wrist or ankle
        t = length - 1.4
        for u in (-1.1, -0.4, 0.4, 1.1):
            px, py = int(x0 + dx * t - dy * u), int(y0 + dy * t + dx * u)
            if 0 <= px < SPRITE_W and 0 <= py < SPRITE_H and rows[py][px]:
                rows[py][px] = KEYS["w"]

    left_arm, right_arm, left_leg, right_leg = POSES[pose]
    hips = len(body) - 0.8
    limb(left + 1.0, shoulder, left_arm, arm, -1)
    limb(left + width - 1.0, shoulder, right_arm, arm, 1)
    limb(left + 2.0, hips, left_leg, leg, -1)
    limb(left + width - 2.0, hips, right_leg, leg, 1)
    for y, line in enumerate(body):
        for x, c in enumerate(line):
            if c != ".":
                rows[y][left + x] = KEYS[c]
    # baked: the dough is darker where it ends to the right or below
    for y in range(SPRITE_H):
        for x in range(SPRITE_W):
            if rows[y][x] == KEYS["b"]:
                if y + 1 == SPRITE_H or x + 1 == SPRITE_W or not rows[y + 1][x] or not rows[y][x + 1]:
                    rows[y][x] = KEYS["o"]
    return rows


class Dancer:
    def __init__(self, group, pal, body, arm, leg, thick, shoulder, x, mirror, order):
        self.sheet = displayio.Bitmap(SPRITE_W * len(POSES), SPRITE_H, len(DOUGH))
        self.feet = []  # lowest row of each pose, so every pose stands on the floor
        for p in range(len(POSES)):
            rows = figure(body, p, arm, leg, thick, shoulder)
            lowest = 0
            for py, row in enumerate(rows):
                for px, value in enumerate(row):
                    if value:
                        self.sheet[p * SPRITE_W + px, py] = value
                        lowest = py
            self.feet.append(lowest)
        self.grid = displayio.TileGrid(self.sheet, pixel_shader=pal.palette, tile_width=SPRITE_W,
                                       tile_height=SPRITE_H, x=x)
        group.append(self.grid)
        self.x = x
        self.mirror = mirror
        self.order = order  # place in the row, for the wave

    def show(self, pose, lift):
        if self.mirror:
            pose = MIRROR[pose]
        self.grid[0] = pose
        self.grid.y = FLOOR - self.feet[pose] - int(lift + 0.5)  # lift in pixels, rounded


class Scene:
    def __init__(self, group, settings):
        self.backdrop(group)
        sheet, w, h = gfx.sprite_sheet(NOTES, {".": 0, "#": 1})
        self.notes = []
        for _ in range(5):
            note_pal = gfx.Pal((0, 0xFFFFFF), transparent=(0,))
            grid = displayio.TileGrid(sheet, pixel_shader=note_pal.palette, tile_width=w, tile_height=h)
            grid.hidden = True
            group.append(grid)  # behind the dancers
            self.notes.append([grid, note_pal, 0.0, 0.0, 9.0, 0xFFFFFF])  # grid, pal, x, y, age, color
        pal = gfx.Pal(DOUGH, transparent=(0,))
        kid_pal = gfx.Pal([gfx.mix(c, 0xFFE0B0, 0.12) for c in DOUGH], transparent=(0,))  # baked lighter
        self.dancers = [
            Dancer(group, pal, PAPA, 5.0, 4.6, 1.15, 8.2, 0, False, 0),
            Dancer(group, kid_pal, KIND, 3.6, 3.4, 1.0, 7.2, 22, False, 1),
            Dancer(group, pal, MAMA, 5.0, 4.6, 1.15, 8.2, 43, True, 2),
        ]
        self.time = 0.0
        self.beat = -1
        self.dance = DANCES[0]
        self.dance_start = 0

    def backdrop(self, group):
        """Baking tray with sprinkles, and a string of lights along the top."""
        count = len(BULBS)
        # 0 clear, 1-3 tray, 4 wire, 5 socket, then the bulbs and their glow, sprinkles, glitter
        colors = [0, 0x3A3E48, 0x6A707E, 0xA8B0C0, 0x1E4630, 0x50505A] + [0] * (2 * count) + list(BULBS)
        self.glitter = len(colors)
        colors += [0, 0, 0]
        self.lights = gfx.Pal(colors)
        bitmap = displayio.Bitmap(64, 32, len(colors))
        for x in range(64):
            bitmap[x, 29] = 3  # the rim of the tray
            bitmap[x, 30] = 2
            bitmap[x, 31] = 1
        for x, i in ((5, 0), (13, 2), (26, 3), (37, 1), (49, 4), (58, 2)):
            bitmap[x, 31] = 6 + 2 * count + i  # sprinkles on the tray
        # the wire hangs in arcs between hooks, a bulb hangs at the bottom of each arc
        for x in range(64):
            bitmap[x, int(0.5 + 2.5 * math.sin(math.pi * (x % 8) / 8))] = 4
        for i in range(8):
            x = 4 + 8 * i
            bulb = 6 + 2 * (i % count)
            bitmap[x, 3] = 5
            bitmap[x, 4] = bulb
            bitmap[x, 5] = bulb
            for gx, gy in ((x - 1, 5), (x + 1, 5), (x, 6), (x - 1, 4), (x + 1, 4)):
                bitmap[gx, gy] = bulb + 1
        # sugar glitter in the air, in three groups that sparkle in turn
        for i in range(14):
            bitmap[random.randrange(64), random.randrange(8, 26)] = self.glitter + i % 3
        group.append(displayio.TileGrid(bitmap, pixel_shader=self.lights.palette))

    def frame(self, dt):
        self.time += dt
        beats = self.time / BEAT
        beat = int(beats)
        part = beats - beat  # 0..1 within the beat
        if beat != self.beat:
            self.beat = beat
            self.on_beat(beat)
        steps, canon = self.dance
        for dancer in self.dancers:
            step = beat - self.dance_start - (dancer.order if canon else 0)
            pose, hop = steps[step % len(steps)] if step >= 0 else (STAND, 0)
            lift = hop * math.sin(math.pi * part)
            if dancer.order == 1:
                lift += abs(math.sin(2 * math.pi * part))  # the little one hops twice a beat
            dancer.show(pose, lift)
        # the colors run along the string on every beat, the bulbs glow brightest on the beat
        glow = 1.0 - 0.45 * part
        for i in range(len(BULBS)):
            color = BULBS[(i + beat) % len(BULBS)]
            self.lights[6 + 2 * i] = gfx.scale(color, glow)
            self.lights[7 + 2 * i] = gfx.scale(color, 0.3 * glow)
        for i in range(3):
            sparkle = max(0.0, math.sin(self.time * (0.9 + 0.35 * i) + 2.1 * i)) ** 4
            self.lights[self.glitter + i] = gfx.scale(0xFFF0C8, sparkle)
        self.float_notes(dt)

    def on_beat(self, beat):
        steps, canon = self.dance
        if beat - self.dance_start >= len(steps) + (2 if canon else 0):
            self.dance = random.choice(DANCES)
            self.dance_start = beat
        if beat % 2 == 0:
            for note in self.notes:
                if note[4] > 3.0:
                    dancer = random.choice(self.dancers)
                    note[0][0] = random.randrange(2)
                    note[2] = dancer.x + random.uniform(4, 14)
                    note[3] = 10.0
                    note[4] = 0.0
                    note[5] = random.choice(NOTE_COLORS)
                    note[0].hidden = False
                    break

    def float_notes(self, dt):
        for note in self.notes:
            grid, pal, x, y, age, color = note
            if age > 3.0:
                continue
            note[4] = age + dt
            note[3] = y - 5.0 * dt
            if note[4] > 3.0 or note[3] < -6:
                grid.hidden = True
                note[4] = 9.0
                continue
            grid.x = int(x + 2.0 * math.sin(age * 2.5))
            grid.y = int(note[3])
            pal[1] = gfx.scale(color, min(1.0, 3.0 - age))
