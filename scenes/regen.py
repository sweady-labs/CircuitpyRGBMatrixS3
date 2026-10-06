"""Regen: rain at night in a street with a lamp, splashes and puddles, now and then soft sheet lightning.

Drops fall with short trails and splash on the wet ground, rings spread in the puddles, the lamp
lights the rain warmly, and distant lightning softly lights up the clouds behind the houses.
The street, the houses and the clouds are one picture, drawn once; the clouds are black until a
lightning lights them, and the lightning, the windows and the shimmer of the reflections only
change its palette. The rain is a layer of its own that is cleared and drawn again every frame: a
few pixels per drop, so it stays cheap even with many drops.
"""
import math
import random

import displayio

from app import gfx

FPS = 25
PREVIEW_AT = 3.0
GROUND = 27  # first row of the street
LAMP_X, LAMP_Y = 47, 10  # the light of the street lamp
CLOUD1, LEVELS = 1, 6  # background palette: clouds in 3 zones (left, middle, right) of 6 levels
WINDOW1, WINDOWS = 19, 4  # lit windows
POLE, LAMP, HALO, PUDDLE, PUDDLE_LIT, REFLECTION, HOUSE = 23, 24, 25, 26, 27, 28, 29
FLASH = 0x98B8E0  # clouds in the light of a lightning (more green than red: no purple when dim)
WINDOW_COLORS = (0xB07830, 0xC89048, 0x9C7840, 0x5070A0)  # lamps, and one TV

# rain layer: 0 transparent; cool drops (head, tail), far drops, warm drops in the lamp light,
# splashes, rings in the puddles (fading), the same in the light of the lamp
RAIN = (0, 0x9AB4D0, 0x3E546C, 0x5C7088, 0x283848, 0xFFE8B8, 0x9C7C48, 0xA8C0D8, 0xFFE0A8,
        0x7890AC, 0x4A5C74, 0x2A3848, 0xE8C080, 0xB08848, 0x785830)
NEAR, NEAR_TAIL, FAR, FAR_TAIL, WARM, WARM_TAIL, SPLASH, SPLASH_WARM = 1, 2, 3, 4, 5, 6, 7, 8
RING1, WARM_RING1 = 9, 12

# puddles on the street: (first x, last x, row)
PUDDLES = ((6, 20, 30), (9, 17, 31), (36, 57, 29), (39, 55, 30), (42, 52, 31), (24, 30, 28))


def in_light(x, y):
    """Inside the cone of light below the lamp?"""
    return y > LAMP_Y and abs(x - LAMP_X) < (y - LAMP_Y) * 0.55 + 1.0


class Scene:
    def __init__(self, group, settings):
        self.back = displayio.Bitmap(64, 32, 32)
        self.back_pal = gfx.Pal([0] * 32)
        group.append(displayio.TileGrid(self.back, pixel_shader=self.back_pal.palette))
        self.draw_street()
        for index, color in ((POLE, 0x3A4448), (LAMP, 0xFFF0C0), (HALO, 0xA87830)):
            self.back_pal[index] = color
        self.windows = [True, True, True, random.random() < 0.5]
        self.lights()

        self.rain = displayio.Bitmap(64, 32, len(RAIN))
        group.append(displayio.TileGrid(self.rain, pixel_shader=gfx.Pal(RAIN, transparent=(0,)).palette))
        self.puddle = bytearray(64 * 32)  # 1 where a drop lands in a puddle
        for x0, x1, y in PUDDLES:
            for x in range(x0, x1 + 1):
                self.puddle[y * 64 + x] = 1

        self.drops = [self.new_drop(random.uniform(-4.0, GROUND)) for _ in range(60)]
        self.splashes = []  # [x, y, dx, age]
        self.rings = []  # [x, y, age]
        self.t = 0.0
        self.flash = 0.0  # brightness of the lightning, 0..1
        self.zone = 1
        self.flashes = []  # times of the coming pulses of a lightning
        self.wait = random.uniform(8.0, 20.0)
        self.clouds()

    # --- the picture behind the rain ------------------------------------------------------

    def draw_street(self):
        b = self.back
        # clouds: soft noise all over the sky, in three zones, so that a lightning can be off to
        # one side
        noise = [[random.random() for _ in range(10)] for _ in range(6)]
        for y in range(GROUND):
            for x in range(64):
                fx, fy = x / 8.0, y / 6.0
                ix, iy = int(fx), int(fy)
                tx, ty = fx - ix, fy - iy
                top = noise[iy][ix] * (1 - tx) + noise[iy][ix + 1] * tx
                bottom = noise[iy + 1][ix] * (1 - tx) + noise[iy + 1][ix + 1] * tx
                value = (top * (1 - ty) + bottom * ty) * 0.8 + 0.2
                b[x, y] = CLOUD1 + min(2, x // 22) * LEVELS + min(LEVELS - 1, int(value * LEVELS))
        # houses: dark facades with rows of windows, some of them lit
        x = random.randint(0, 2)
        while x < 38:
            width, top = random.randint(8, 12), random.randint(11, 18)
            for px in range(x, min(40, x + width)):
                for y in range(top, GROUND):
                    b[px, y] = HOUSE
            if random.random() < 0.5:  # a pitched roof
                for i in range(1, width // 2 + 1):
                    for px in range(x + i, min(40, x + width - i)):
                        b[px, top - i] = HOUSE
            awake = random.uniform(0.25, 0.55)  # how many people are still up in this house
            for wy in range(top + 2, GROUND - 2, 3):
                for wx in range(x + 1, min(38, x + width - 2), 3):
                    if random.random() < awake:
                        window = WINDOW1 + random.randrange(WINDOWS)
                        b[wx, wy] = window
                        b[wx + 1, wy] = window
            x += width + random.randint(1, 2)
        for px in range(41, 64):  # low roofs behind the lamp
            for y in range(19 + (px // 6) % 2 * 2, GROUND):
                b[px, y] = 0
        # the street is black and wet: puddles mirror the lamp and the lightning
        for x0, x1, y in PUDDLES:
            for x in range(x0, x1 + 1):
                b[x, y] = PUDDLE_LIT if in_light(x, y) else PUDDLE
        for y in range(GROUND + 2, 32):
            b[LAMP_X, y] = REFLECTION
        # the street lamp: pole, arm and light
        for y in range(LAMP_Y, GROUND):
            b[LAMP_X + 4, y] = POLE
        for x in range(LAMP_X, LAMP_X + 5):
            b[x, LAMP_Y - 1] = POLE
        b[LAMP_X, LAMP_Y] = LAMP
        b[LAMP_X - 1, LAMP_Y] = HALO
        b[LAMP_X + 1, LAMP_Y] = HALO
        b[LAMP_X, LAMP_Y + 1] = HALO

    def clouds(self):
        """A lightning lights the clouds, most in its own zone; the houses stand dark against
        them and the puddles mirror the light."""
        for zone in range(3):
            light = self.flash * (1.0, 0.45, 0.15)[abs(zone - self.zone)]
            for level in range(LEVELS):
                thickness = (level / (LEVELS - 1)) ** 1.5
                self.back_pal[CLOUD1 + zone * LEVELS + level] = gfx.scale(FLASH, light * thickness)
        self.back_pal[HOUSE] = gfx.scale(0x141A28, 1.0 - min(1.0, self.flash * 2.0))
        self.back_pal[PUDDLE] = gfx.mix(0x141C28, FLASH, self.flash * 0.5)

    def lights(self):
        for i, on in enumerate(self.windows):
            self.back_pal[WINDOW1 + i] = WINDOW_COLORS[i] if on else 0

    # --- rain --------------------------------------------------------------------------------

    def new_drop(self, y=None):
        """[x, y, speed, near, row where it lands]: near drops are faster and brighter and land
        further in front."""
        near = random.random() < 0.55
        speed = random.uniform(46.0, 60.0) if near else random.uniform(26.0, 34.0)
        land = random.randint(29, 31) if near else random.randint(GROUND, GROUND + 1)
        return [random.uniform(-8.0, 72.0), random.uniform(-12.0, -1.0) if y is None else y, speed, near, land]

    def frame(self, dt):
        self.t += dt
        t = self.t
        rain = self.rain
        rain.fill(0)
        wind = -0.18 + 0.14 * math.sin(t * 0.05)  # pixels sideways per pixel down
        wanted = int(55 + 25 * math.sin(t * 0.021))  # the rain gets heavier and lighter
        alive = []
        for drop in self.drops:
            x, y, speed, near, land = drop
            y += speed * dt
            x += speed * dt * wind
            if y >= land:
                self.landed(int(x), land, near)
                if len(self.drops) <= wanted:
                    alive.append(self.new_drop())
                continue
            drop[0], drop[1] = x, y
            alive.append(drop)
            # head and a short trail up against the wind; warm in the light of the lamp
            iy = int(y)
            if in_light(int(x), iy):
                head, tail = WARM, WARM_TAIL
            elif near:
                head, tail = NEAR, NEAR_TAIL
            else:
                head, tail = FAR, FAR_TAIL
            for k in range(4 if near else 2):
                px = int(x - k * wind)
                if 0 <= px < 64 and iy >= k:
                    rain[px, iy - k] = tail if k else head
        while len(alive) < wanted:
            alive.append(self.new_drop())
        self.drops = alive

        self.draw_splashes(dt)
        flash = self.flash
        self.lightning(dt)
        if self.flash or flash:
            self.clouds()
        if random.random() < dt / 20.0:  # now and then a light goes on or off
            i = random.randrange(WINDOWS)
            self.windows[i] = not self.windows[i]
            self.lights()
        # the reflections of the lamp shimmer on the wet street
        shimmer = 0.5 + 0.5 * math.sin(t * 7.0) * math.sin(t * 2.3)
        self.back_pal[PUDDLE_LIT] = gfx.scale(0x6A4C20, 0.85 + 0.15 * shimmer)
        self.back_pal[REFLECTION] = gfx.scale(0xD8A050, 0.7 + 0.3 * shimmer)

    def landed(self, x, y, near):
        if not (0 <= x < 64):
            return
        if self.puddle[y * 64 + x]:
            if len(self.rings) < 8:
                self.rings.append([x, y, 0.0])
        elif near and len(self.splashes) < 16:
            for dx in (-1, 1):
                self.splashes.append([x, y, dx, 0.0])

    def draw_splashes(self, dt):
        """Splashes: two tiny droplets jump up and fall back. Rings: grow and fade in the puddles."""
        rain = self.rain
        keep = []
        for splash in self.splashes:
            x, y, dx, age = splash
            age += dt
            if age < 0.24:
                splash[3] = age
                keep.append(splash)
                px = x + dx * (1 + int(age * 8))
                py = y - (1 if age < 0.16 else 0) - (1 if 0.04 < age < 0.12 else 0)
                if 0 <= px < 64:
                    rain[px, py] = SPLASH_WARM if in_light(px, py) else SPLASH
        self.splashes = keep
        keep = []
        for ring in self.rings:
            x, y, age = ring
            age += dt
            if age < 0.6:
                ring[2] = age
                keep.append(ring)
                radius = 1 + int(age * 6)
                value = (WARM_RING1 if in_light(x, y) else RING1) + min(2, int(age * 5))
                for px in (x - radius, x + radius):
                    if 0 <= px < 64 and self.puddle[y * 64 + px]:
                        rain[px, y] = value
                if radius > 2:  # a wider ring also shows its far side, one row up
                    for px in range(x - radius + 2, x + radius - 1, 2):
                        if 0 <= px < 64 and y > GROUND and self.puddle[(y - 1) * 64 + px]:
                            rain[px, y - 1] = value
        self.rings = keep

    def lightning(self, dt):
        """Distant sheet lightning: one to three soft pulses that swell and fade slowly, no flashes."""
        self.wait -= dt
        if self.wait <= 0 and not self.flashes:
            self.wait = random.uniform(25.0, 70.0)
            self.zone = random.randrange(3)
            start = self.t
            self.flashes = [(start, random.uniform(0.55, 0.8))]
            for _ in range(random.randint(0, 2)):
                start += random.uniform(0.4, 0.9)
                self.flashes.append((start, random.uniform(0.25, 0.55)))
        light = 0.0
        for start, strength in self.flashes:
            age = self.t - start
            if age > 0:
                light = max(light, strength * min(1.0, age / 0.25) * math.exp(-max(0.0, age - 0.25) / 0.8))
        self.flash = light
        if self.flashes and self.t - self.flashes[-1][0] > 5.0:
            self.flashes = []
