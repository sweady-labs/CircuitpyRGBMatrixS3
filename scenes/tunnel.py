"""Tunnel: flight through a neon tube, demo-scene style, with depth fog, colour shifts and curves.

For every pixel three bytes are computed once at the start: the angle around the tube, the depth
(inversely proportional to the distance from the vanishing point) and a fog zone. Per frame only a
few byte operations remain: rotation and the distance flown are added to angle and depth (bytes
wrap around at 256, so the texture repeats by itself), a shift keeps the top bits, and the zone is
added. The palettes draw everything. Two layers:

    rings:  index = zone * 32 + depth step (0-31), two rings per 32 steps, the wall in between
    spokes: index = zone * 8 + angle step (0-7), only step 0 is a colour, the rest is transparent

Each palette entry knows how deep in the fog it lies; the far zones are dimmer and shifted in
hue, so the colour changes with depth. The tables are twice the size of the screen; a moving
window into them shifts the vanishing point, which makes the tube seem to bend.
"""
import math

import bitmaptools
from ulab import numpy as np

from app import gfx

FPS = 25
PREVIEW_AT = 3.0

DEPTH = 4000.0  # depth = DEPTH / distance in pixels; a ring every 128
SPOKES = 8  # the angle byte runs through 256 once per spoke
ZONES = 8  # fog: 0 black at the vanishing point ... 7 full colour
STEPS = 32  # depth steps per 256: 16 per ring


def wrapped_bytes(values):
    """Float array -> bytes, wrapping around at 256 like the texture does."""
    return np.array(np.bitwise_and(np.array(values, dtype=np.int16), 255), dtype=np.uint8)


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * (ZONES * STEPS))
        self.spokes, self.spoke_pal = gfx.canvas(group, [0] * (ZONES * 8),
                                                 transparent=[i for i in range(ZONES * 8) if i % 8])
        # tables for a field of 128 x 64 pixels with the vanishing point in its middle
        dx = np.zeros((64, 128)) + np.linspace(-63.5, 63.5, 128).reshape((1, 128))
        dy = np.zeros((64, 128)) + np.linspace(-31.5, 31.5, 64).reshape((64, 1))
        distance = np.sqrt(dx * dx + dy * dy)
        self.angle = wrapped_bytes((np.arctan2(dy, dx) * (1 / (2 * math.pi)) + 0.5) * (SPOKES * 256))
        self.depth = wrapped_bytes(DEPTH / distance)
        # fog zones: black up to 2 pixels from the vanishing point, full colour from 16 on
        zone = np.array(np.clip((distance - 2.0) * ((ZONES - 1) / 14.0), 0, ZONES - 1), dtype=np.uint8)
        self.zone_rings = zone * STEPS
        self.zone_spokes = zone * 8
        self.t = 0.0
        self.travel = 0.0
        self.spin = 0.0
        self.hue = 0.55
        self.next_zone = 1
        for zone in range(ZONES):
            self.paint(zone)

    def paint(self, zone):
        """Colours of one fog zone in both palettes."""
        fog = (zone / (ZONES - 1)) ** 1.3
        # the far zones are shifted in hue: the colour changes with depth
        color = gfx.hsv(self.hue + 0.12 * (ZONES - 1 - zone) / (ZONES - 1), 0.85, 1.0)
        core = gfx.scale(gfx.mix(color, 0xFFFFFF, 0.35), fog)
        glow = gfx.scale(color, 0.45 * fog)
        walls = (gfx.scale(color, 0.18 * fog), gfx.scale(color, 0.1 * fog))
        first = zone * STEPS
        for step in range(STEPS):
            ring = step & 15  # 0 is the ring itself
            if ring == 0:
                c = core
            elif ring in (1, 15):
                c = glow
            else:
                c = walls[ring >= 8]  # every ring section has a lighter and a darker half
            self.pal[first + step] = c
        self.spoke_pal[zone * 8] = gfx.scale(color, 0.7 * fog)

    def frame(self, dt):
        self.t += dt
        t = self.t
        # speed and rotation swell and ebb; the rotation changes direction now and then
        self.travel = (self.travel + dt * (110.0 + 50.0 * math.sin(t * 0.11))) % 256
        self.spin = (self.spin + dt * 60.0 * math.sin(t * 0.07)) % 256
        # vanishing point: the window into the tables wanders on slow sine waves
        ox = int(32 + 7 * math.sin(t * 0.23) + 2 * math.sin(t * 0.61))
        oy = int(16 + 4 * math.sin(t * 0.17 + 1.3))

        # bytes wrap around at 256, so adding the motion is all the texture needs
        v = self.depth[oy:oy + 32, ox:ox + 64] + int(self.travel)
        rings = np.right_shift(v, 3) + self.zone_rings[oy:oy + 32, ox:ox + 64]
        bitmaptools.arrayblit(self.bitmap, rings)
        u = self.angle[oy:oy + 32, ox:ox + 64] + int(self.spin)
        spokes = np.right_shift(u, 5) + self.zone_spokes[oy:oy + 32, ox:ox + 64]
        bitmaptools.arrayblit(self.spokes, spokes)

        # the colours drift; one fog zone is repainted per frame (zone 0 stays black)
        self.hue = (self.hue + dt * 0.008) % 1.0
        self.paint(self.next_zone)
        self.next_zone = self.next_zone % (ZONES - 1) + 1
