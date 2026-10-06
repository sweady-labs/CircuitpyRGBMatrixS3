"""Laufschrift: the message from the web interface in large letters.

Short texts stand still in the middle, longer ones scroll through. A soft glint runs across
the letters; with the color "bunt" the rainbow flows through the text instead.
"""
import math

import displayio

from app import font, gfx

FPS = 30
PREVIEW_AT = 2.5
SPEEDS = (0, 12, 20, 30, 42, 58)  # pixels per second for speed 1..5
BANDS = 24  # color bands across the text for glint and rainbow
GAP = 24  # pixels between the end and the next start when scrolling


class Scene:
    def __init__(self, group, settings):
        message = settings["message"]
        self.text = message["text"]
        self.rainbow = message["color"] == "bunt"
        self.color = 0xFFFFFF if self.rainbow else int(message["color"][1:], 16)
        self.speed = SPEEDS[message["speed"]]

        width = max(1, gfx.text_width(self.text))
        bitmap = displayio.Bitmap(width, font.NORMAL_HEIGHT, BANDS + 1)
        gfx.draw_text(bitmap, self.text, 0, 0, lambda px, py: 1 + (px // 2) % BANDS)
        self.pal = gfx.Pal([0] * (BANDS + 1), transparent=(0,))

        self.scaled = displayio.Group(scale=2)
        self.grid = displayio.TileGrid(bitmap, pixel_shader=self.pal.palette)
        self.scaled.append(self.grid)
        group.append(self.scaled)

        self.width = width * 2
        self.scroll = self.width > 62
        self.scaled.y = 8
        self.x = 64.0 if self.scroll else (64 - self.width) / 2
        self.phase = 0.0

    def frame(self, dt):
        self.phase += dt
        for band in range(BANDS):
            pos = band / BANDS
            if self.rainbow:
                color = gfx.hsv(pos - self.phase * 0.15, 0.85, 1.0)
            else:
                # glint: a bright wave moving along the text every few seconds
                wave = math.cos((pos - self.phase * 0.35) * 2 * math.pi)
                glint = max(0.0, wave) ** 12
                color = gfx.mix(gfx.scale(self.color, 0.82), 0xFFFFFF, glint * 0.55)
            self.pal[band + 1] = color

        if self.scroll:
            self.x -= self.speed * dt
            if self.x < -self.width - GAP:
                self.x = 64.0
        self.scaled.x = int(self.x)
