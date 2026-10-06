"""Sternenflug: flight through a starfield, calm cruising alternating with jumps into hyperspace.

Every star has a place in space (x, y and the distance z) and is projected onto the screen; the
closer it comes, the brighter it gets. While cruising the stars drift outwards as points. Before a
jump the ship speeds up and the stars stretch into streaks: a line from where the star was a moment
ago to where it is now, so the streaks grow with the speed by themselves. After the jump the ship
brakes in a new region with a different mix of star colours. The vanishing point wanders a little
and the view rolls slowly, as if the ship were steering.
"""
import math
import random

import bitmaptools

from app import gfx

FPS = 25
PREVIEW_AT = 5.3  # in the middle of the first jump

STARS = 100
FOCAL = 16.0  # pixels: a star at x = 1, z = 1 is 16 pixels from the vanishing point
Z_FAR = 3.2
Z_NEAR = 0.15
SPREAD_X = 5.0  # stars are born in this box at Z_FAR
SPREAD_Y = 2.6
CRUISE_SPEED = 0.35  # depth units per second
JUMP_SPEED = 14.0
TRAIL_TIME = 0.07  # a streak shows where the star was this many seconds ago
SPOOL, JUMP, BRAKE = 1.8, 2.6, 2.2  # seconds of speeding up, hyperspace and braking
FIRST_CRUISE = 3.0  # short, so a jump comes soon after the start (and in the preview)

LEVELS = 8  # brightness steps per star colour
WARP_STEPS = 12  # precomputed palettes between cruising and hyperspace
# star colours from faint to bright: blue, white, yellow, orange, red. Faint stars get a more
# saturated tint of their colour, so they stay colourful instead of turning grey.
COLORS = ((0x3050FF, 0xA8C0FF), (0x6078FF, 0xFFFFFF), (0xE0A030, 0xFFF0B0), (0xFF6020, 0xFFB070),
          (0xE02818, 0xFF7058))
HYPER = (0x4870FF, 0xE4EEFF)  # in hyperspace every star turns blue, the bright ones blue-white
# star colour mixes of the regions the ship arrives in (weights for COLORS)
REGIONS = ((3, 4, 2, 1, 0), (1, 3, 3, 2, 1), (4, 2, 1, 0, 0), (1, 2, 3, 3, 2), (2, 4, 2, 1, 1))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def palette(warp):
    colors = [0]
    for faint, bright in COLORS:
        for level in range(LEVELS):
            share = level / (LEVELS - 1)
            color = gfx.mix(gfx.mix(faint, bright, share), gfx.mix(HYPER[0], HYPER[1], share), warp)
            colors.append(gfx.scale(color, 0.3 + 0.7 * share))
    return colors


class Scene:
    def __init__(self, group, settings):
        self.palettes = [palette(step / (WARP_STEPS - 1)) for step in range(WARP_STEPS)]
        self.step = 0
        self.bitmap, self.pal = gfx.canvas(group, self.palettes[0])
        self.region = random.choice(REGIONS)
        self.stars = [self.new_star(random.uniform(Z_NEAR + 0.3, Z_FAR)) for _ in range(STARS)]
        self.t = 0.0
        self.phase = "cruise"
        self.phase_time = 0.0
        self.phase_length = FIRST_CRUISE

    def new_star(self, z):
        weights = self.region
        pick = random.random() * sum(weights)
        family = 0
        while pick >= weights[family]:
            pick -= weights[family]
            family += 1
        x = random.uniform(-SPREAD_X, SPREAD_X)
        y = random.uniform(-SPREAD_Y, SPREAD_Y)
        if abs(x) < 0.08 and abs(y) < 0.08:  # a star on the axis would stand still in the middle
            x = 0.3
        # [x, y, z, first palette index of its colour, own brightness]
        return [x, y, z, 1 + family * LEVELS, random.uniform(0.55, 1.0)]

    def warp(self, dt):
        """0 while cruising ... 1 in hyperspace; moves through the phases."""
        self.phase_time += dt
        if self.phase_time >= self.phase_length:
            self.phase_time = 0.0
            if self.phase == "cruise":
                self.phase, self.phase_length = "spool", SPOOL
            elif self.phase == "spool":
                self.phase, self.phase_length = "jump", JUMP
            elif self.phase == "jump":
                self.phase, self.phase_length = "brake", BRAKE
                self.region = random.choice(REGIONS)  # from now on stars are born in the new colours
            else:
                self.phase, self.phase_length = "cruise", random.uniform(16.0, 30.0)
        progress = self.phase_time / self.phase_length
        if self.phase == "spool":
            return smooth(progress)
        if self.phase == "jump":
            return 1.0
        if self.phase == "brake":
            return 1.0 - smooth(progress)
        return 0.0

    def frame(self, dt):
        self.t += dt
        t = self.t
        warp = self.warp(dt)
        step = int(warp * (WARP_STEPS - 1) + 0.5)
        if step != self.step:
            self.step = step
            self.pal.set_all(self.palettes[step])

        # speed grows exponentially with the warp, so speeding up feels like a steady push
        cruise = CRUISE_SPEED * (1.0 + 0.25 * math.sin(t * 0.05))
        speed = cruise * (JUMP_SPEED / cruise) ** warp
        move = speed * dt
        trail = speed * TRAIL_TIME
        # the ship steers gently: vanishing point and roll drift on slow sine waves; for a jump
        # it lines up, so the streaks fly straight out of the middle
        steer = 1.0 - warp
        cx = 32.0 + steer * (7.0 * math.sin(t * 0.071) + 3.0 * math.sin(t * 0.23))
        cy = 16.0 + steer * 3.5 * math.sin(t * 0.093 + 1.0)
        roll = 0.3 * math.sin(t * 0.041)
        cos_r = math.cos(roll) * FOCAL
        sin_r = math.sin(roll) * FOCAL

        bitmap = self.bitmap
        bitmap.fill(0)
        top = LEVELS - 1
        for star in self.stars:
            z = star[2] - move
            if z < Z_NEAR:
                star[:] = self.new_star(Z_FAR - random.random() * 0.4)
                continue
            star[2] = z
            x, y = star[0], star[1]
            # rotated and scaled once, divided by the distance twice (head now, tail a moment ago)
            rx = x * cos_r - y * sin_r
            ry = x * sin_r + y * cos_r
            hx = cx + rx / z
            hy = cy + ry / z
            tz = z + trail
            tx = cx + rx / tz
            ty = cy + ry / tz
            if not (-1.0 <= tx < 65.0 and -1.0 <= ty < 33.0):
                star[:] = self.new_star(Z_FAR - random.random() * 0.4)
                continue
            near = (Z_FAR + 0.2 - z) * 0.45  # 0.1 at the far end, 1 from z = 1.2 on
            # in hyperspace only the brighter stars remain: a few clear streaks instead of a tangle
            shine = star[4] * max(0.0, 1.0 - warp * (1.0 - star[4]) * 3.5)
            level = int(top * shine * min(1.0, near) + 0.5)
            if level < 1 and warp > 0.0:
                continue
            base = star[3]
            ix, iy = int(hx), int(hy)
            if abs(hx - tx) + abs(hy - ty) >= 1.5:
                # streak: dim tail half, brighter front half, the star itself at the head
                mx, my = int((hx + tx) * 0.5), int((hy + ty) * 0.5)
                bitmaptools.draw_line(bitmap, int(tx), int(ty), mx, my, base + max(0, level - 3))
                bitmaptools.draw_line(bitmap, mx, my, ix, iy, base + max(0, level - 1))
            elif level >= 5 and z < 1.0 and 1 <= ix < 63 and 1 <= iy < 31:
                # close stars are bigger: a small cross with dim arms
                arm = base + level - 5
                bitmap[ix - 1, iy] = arm
                bitmap[ix + 1, iy] = arm
                bitmap[ix, iy - 1] = arm
                bitmap[ix, iy + 1] = arm
            if 0 <= ix < 64 and 0 <= iy < 32:
                bitmap[ix, iy] = base + level
