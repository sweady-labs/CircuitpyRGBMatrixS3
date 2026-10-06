"""Atmen: a soft light that grows for 4 seconds (breathe in) and shrinks for 6 seconds (breathe out).

Every pixel holds its distance from the middle in quarter pixels; that picture is drawn once and
never changes. The animation is only the palette: each frame computes the color for every distance
from the current size of the light, so it grows and shrinks smoothly, in steps much finer than a
pixel. A thin ring shows the direction: it gathers in from the edges while breathing in and drifts
outwards while breathing out. The colors wander slowly through calm hues.
"""
import math

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 25
PREVIEW_AT = 3.6  # almost fully breathed in
IN_SECONDS = 4.0
OUT_SECONDS = 6.0
STEPS = 4  # palette entries per pixel of distance
R_SMALL, R_BIG = 3.5, 11.5  # radius of the light, breathed out and breathed in
R_FAR = 34.0  # where the ring starts and ends, beyond the corners of the screen
GLOW = 2.2  # pixels in which the glow around the light fades to a third
THEME_SECONDS = 30.0  # three breaths per color

# (core, rim) of the light; the colors blend from one pair to the next
THEMES = (
    (0xC8FFEC, 0x10D4A0),  # teal
    (0xD4E4FF, 0x3A78FF),  # blue
    (0xF0DCFF, 0x9A5AFF),  # violet
    (0xFFDCEA, 0xFF5A98),  # rose
    (0xFFEBCC, 0xFF9A38),  # amber
    (0xDCFFD8, 0x40DC7C),  # green
)


def ease(x):
    """0..1 -> 0..1, starting and ending gently like a breath."""
    return 0.5 - 0.5 * math.cos(math.pi * x)


class Scene:
    def __init__(self, group, settings):
        xs = np.linspace(-31.5, 31.5, 64).reshape((1, 64))
        ys = np.linspace(-15.5, 15.5, 32).reshape((32, 1))
        distance = np.sqrt(xs * xs + ys * ys) * STEPS
        self.count = int(np.max(distance)) + 2
        self.bitmap, self.pal = gfx.canvas(group, [0] * self.count)
        bitmaptools.arrayblit(self.bitmap, np.array(distance, dtype=np.uint8))  # ulab rounds to the nearest step
        self.t = 0.0

    def colors(self):
        """(core, rim) as (r, g, b), blended between the themes."""
        pos = self.t / THEME_SECONDS
        i = int(pos)
        blend = ease(pos - i)
        a = THEMES[i % len(THEMES)]
        b = THEMES[(i + 1) % len(THEMES)]
        return [gfx.split(gfx.mix(a[k], b[k], blend)) for k in range(2)]

    def frame(self, dt):
        self.t += dt
        phase = self.t % (IN_SECONDS + OUT_SECONDS)
        if phase < IN_SECONDS:
            x = phase / IN_SECONDS
            full = ease(x)
            radius = R_SMALL + (R_BIG - R_SMALL) * full
            # the ring comes in from far away and arrives at the light when the breath is complete
            ring = radius + (R_FAR - R_BIG) * (1.0 - x) ** 1.4
            ring_light = 0.38 * min(1.0, x * 3.0) * min(1.0, (1.0 - x) * 6.0)
        else:
            x = (phase - IN_SECONDS) / OUT_SECONDS
            full = 1.0 - ease(x)
            radius = R_SMALL + (R_BIG - R_SMALL) * full
            # the ring leaves the light and fades while it drifts outwards
            ring = R_BIG + (R_FAR - R_BIG) * x ** 0.8
            ring_light = 0.38 * min(1.0, x * 8.0) * (1.0 - x) ** 1.5

        (cr, cg, cb), (er, eg, eb) = self.colors()
        light = 0.75 + 0.25 * full  # breathed in, the light is brighter
        # The glow outside the sphere fades by the same factor from one entry to the next, so it
        # needs a single exp per frame; this loop runs for every entry and is kept lean.
        inside = int(radius * STEPS) + 1
        glow = light * 0.55 * math.exp((radius - inside / STEPS) / GLOW)
        fade = math.exp(-1.0 / (STEPS * GLOW))
        colors = []
        for i in range(self.count):
            d = i / STEPS
            near = d - ring
            if i < inside:
                # a sphere of light: a pale core, deepening towards the saturated rim
                s = d / radius
                core = (1.0 - s) * (1.0 - s)
                v = light * (1.0 - 0.45 * s * s)
                r = (er + (cr - er) * core) * v
                g = (eg + (cg - eg) * core) * v
                b = (eb + (cb - eb) * core) * v
            elif glow > 0.004 or -2.5 < near < 2.5:
                r = er * glow
                g = eg * glow
                b = eb * glow
                glow *= fade
            else:
                colors.append(0)
                continue
            if -2.5 < near < 2.5:
                band = ring_light * math.exp(-near * near * 1.2)
                r += er * band
                g += eg * band
                b += eb * band
            colors.append((min(255, int(r)) << 16) | (min(255, int(g)) << 8) | min(255, int(b)))
        self.pal.set_all(colors)
