"""Leuchtbälle: glowing balls that fall, bounce off the walls and off each other.

Each ball is a sprite computed once at the start (with ulab, for all pixels at once): a bright
spot of light, the coloured body with a soft edge and a faint glow around it. The sprite sheet
holds it 4 x 4 times, shifted by quarter pixels, so a slow ball glides smoothly instead of jumping
from pixel to pixel; moving a ball means moving its TileGrid and picking a tile, almost free.
Glows lie on a layer below all bodies, so a neighbour's glow never cuts into a ball. Two dimmer
copies follow each ball a few frames behind as its trail. Balls flash up when they hit something.

The physics: gravity that tilts slowly to the left and right, bouncing walls, collisions between
balls with their masses (area), and now and then a kick for a ball that has come to rest.
"""
import math
import random

import bitmaptools
import displayio
from ulab import numpy as np

from app import gfx

FPS = 25
PREVIEW_AT = 3.0

COLORS = (0xFF5E6C, 0xFFB03A, 0x4DFFB0, 0x45B8FF, 0xA98BFF, 0xFF73D2, 0xD8FF5A)
SUB = 4  # sub-pixel steps per pixel
GLOW = 2.0  # pixels of glow around a ball
LEVELS = 12  # palette entries per ball, 0 transparent
FLASHES = 4  # precomputed palettes from calm to flashing
GRAVITY = 32.0  # pixels per second squared
BOUNCE = 0.88  # speed kept at a wall
HISTORY = 7  # frames of positions remembered for the trail
GHOSTS = ((3, 0.42), (6, 0.18))  # (frames behind, brightness)


def level_colors(color, flash):
    """Palette of a ball: glow (dim, saturated), body, then the spot of light turning white."""
    color = gfx.mix(color, 0xFFFFFF, 0.15 * flash)
    colors = [0]
    for level in range(1, LEVELS):
        v = level / (LEVELS - 1)
        shade = gfx.scale(color, min(1.0, v / 0.85 + 0.12 * flash))
        colors.append(gfx.mix(shade, 0xFFFFFF, max(0.0, v - 0.85) / 0.15 * 0.7))
    return colors


def sprite_sheets(radius, size):
    """Two bitmaps of SUB x SUB tiles: the whole ball with its glow, and only its body."""
    # x and y of every pixel centre relative to the ball centre, tile by tile
    offsets = [px + 0.5 - (size // 2 + tile / SUB) for tile in range(SUB) for px in range(size)]
    dx = np.array(offsets).reshape((1, size * SUB))
    dy = np.array(offsets).reshape((size * SUB, 1))
    distance = np.sqrt(dx * dx + dy * dy)
    # shaded like a sphere lit from the upper left, with a spot of light; the dark side stays
    # fairly bright, the balls glow by themselves
    nz = np.sqrt(np.clip(1.0 - (dx * dx + dy * dy) / (radius * radius), 0.0, 1.0))
    lit = np.clip((dx * -0.45 + dy * -0.55) / radius + nz * 0.7, 0.0, 1.0)
    hx = dx + radius * 0.38
    hy = dy + radius * 0.42
    spot = np.clip(1.0 - np.sqrt(hx * hx + hy * hy) / (radius * 0.5), 0.0, 1.0)
    body = 0.5 + 0.36 * lit + 0.3 * spot * spot
    cover = np.clip(radius + 0.5 - distance, 0.0, 1.0)  # soft edge
    glow = 0.4 * np.exp(np.clip(distance - radius, 0.0, 9.0) * -1.4)
    top = LEVELS - 1
    sheets = []
    for value in (cover * body + (1.0 - cover) * glow, cover * body):
        sheet = displayio.Bitmap(size * SUB, size * SUB, LEVELS)
        bitmaptools.arrayblit(sheet, np.array(np.clip(value * top, 0, top), dtype=np.uint8))  # ulab rounds
        sheets.append(sheet)
    return sheets


class Ball:
    def __init__(self, color, groups):
        glows, bodies, ghosts = groups
        self.r = random.uniform(2.4, 3.8)
        self.mass = self.r * self.r
        self.x = random.uniform(self.r, 64 - self.r)
        self.y = random.uniform(self.r, 20)
        self.vx = random.uniform(-20, 20)
        self.vy = random.uniform(-10, 10)
        self.flash = 0.0
        self.shown_flash = 0
        self.history = [(self.x, self.y)] * HISTORY
        self.size = int(2 * (self.r + GLOW)) + 2
        whole, body = sprite_sheets(self.r, self.size)
        self.palettes = [level_colors(color, f / (FLASHES - 1)) for f in range(FLASHES)]
        self.pal = gfx.Pal(self.palettes[0], transparent=(0,))
        self.grids = []
        for sheet, group in ((whole, glows), (body, bodies)):
            grid = displayio.TileGrid(sheet, pixel_shader=self.pal.palette, tile_width=self.size,
                                      tile_height=self.size)
            group.append(grid)
            self.grids.append(grid)
        self.ghosts = []
        for behind, shine in GHOSTS:
            pal = gfx.Pal([gfx.scale(c, shine) for c in self.palettes[0]], transparent=(0,))
            grid = displayio.TileGrid(whole, pixel_shader=pal.palette, tile_width=self.size, tile_height=self.size)
            ghosts.append(grid)
            self.ghosts.append((behind, grid))

    def place(self, grid, x, y):
        """Moves a sprite so that the ball's centre is at x, y (to a quarter pixel)."""
        ix, iy = math.floor(x), math.floor(y)  # floor, not int: a ball pushed past the edge stays valid
        grid.x = ix - self.size // 2
        grid.y = iy - self.size // 2
        grid[0] = int((y - iy) * SUB) * SUB + int((x - ix) * SUB)

    def show(self):
        self.history.pop(0)
        self.history.append((self.x, self.y))
        for grid in self.grids:
            self.place(grid, self.x, self.y)
        for behind, grid in self.ghosts:
            x, y = self.history[-1 - behind]
            self.place(grid, x, y)
        flash = min(FLASHES - 1, int(self.flash * FLASHES))
        if flash != self.shown_flash:
            self.shown_flash = flash
            self.pal.set_all(self.palettes[flash])


class Scene:
    def __init__(self, group, settings):
        ghosts, glows, bodies = displayio.Group(), displayio.Group(), displayio.Group()
        for layer in (ghosts, glows, bodies):
            group.append(layer)
        self.balls = [Ball(color, (glows, bodies, ghosts)) for color in COLORS]
        self.t = 0.0
        self.kick_wait = 2.0

    def hit(self, ball, speed):
        ball.flash = max(ball.flash, min(1.0, speed / 40.0))

    def move(self, dt, gx, gy):
        balls = self.balls
        for b in balls:
            b.vx += gx * dt
            b.vy += gy * dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            r = b.r
            if b.x < r and b.vx < 0:
                b.x, b.vx = r, -b.vx * BOUNCE
                self.hit(b, -b.vx)
            elif b.x > 64 - r and b.vx > 0:
                b.x, b.vx = 64 - r, -b.vx * BOUNCE
                self.hit(b, b.vx)
            if b.y > 32 - r and b.vy > 0:
                # a hard landing flashes, a soft one just settles (no endless tiny hops)
                b.y = 32 - r
                b.vy = -b.vy * BOUNCE if b.vy > 6.0 else 0.0
                b.vx *= 0.985  # rolling on the floor slows a little
                self.hit(b, -b.vy)
            elif b.y < r and b.vy < 0:
                b.y, b.vy = r, -b.vy * BOUNCE
                self.hit(b, b.vy)
        for i in range(len(balls)):
            a = balls[i]
            for j in range(i + 1, len(balls)):
                b = balls[j]
                dx = b.x - a.x
                dy = b.y - a.y
                reach = a.r + b.r
                d2 = dx * dx + dy * dy
                if d2 >= reach * reach or d2 < 1e-6:
                    continue
                d = math.sqrt(d2)
                nx, ny = dx / d, dy / d
                # push apart, the lighter ball moves more
                share = b.mass / (a.mass + b.mass)
                overlap = reach - d
                a.x -= nx * overlap * share
                a.y -= ny * overlap * share
                b.x += nx * overlap * (1 - share)
                b.y += ny * overlap * (1 - share)
                closing = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
                if closing < 0:
                    impulse = -1.9 * closing / (1 / a.mass + 1 / b.mass)  # almost elastic
                    a.vx -= impulse * nx / a.mass
                    a.vy -= impulse * ny / a.mass
                    b.vx += impulse * nx / b.mass
                    b.vy += impulse * ny / b.mass
                    self.hit(a, -closing)
                    self.hit(b, -closing)

    def frame(self, dt):
        self.t += dt
        # gravity tilts a little, slowly, so the balls roll to one side and back
        tilt = 0.15 * math.sin(self.t * 0.09)
        gx, gy = GRAVITY * math.sin(tilt), GRAVITY * math.cos(tilt)
        for _ in range(2):  # two half steps keep fast collisions clean
            self.move(dt / 2, gx, gy)

        # now and then a ball lying on the floor jumps up again, so the play never ends
        self.kick_wait -= dt
        if self.kick_wait <= 0.0:
            self.kick_wait = random.uniform(0.6, 2.0)
            lying = [b for b in self.balls if b.y > 31 - b.r - 1.0 and abs(b.vy) < 8.0]
            if lying:
                b = random.choice(lying)
                b.vy = -random.uniform(30.0, 44.0)
                b.vx += random.uniform(-18.0, 18.0)
                b.flash = 1.0

        for b in self.balls:
            b.flash = max(0.0, b.flash - dt * 2.5)
            b.show()
