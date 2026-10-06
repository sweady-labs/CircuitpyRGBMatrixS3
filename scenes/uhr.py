"""Uhr: große Ziffern, Datum und ein Sekundenbalken. Die Farben wandern mit der Tageszeit."""
import math

import bitmaptools

from app import clock, font, gfx

FPS = 20
PREVIEW_AT = 1.5

# (from hour, top color, bottom color); during the last hour before the next entry the colors blend over
THEMES = (
    (0, 0xFF6A3D, 0xA0200A),  # night: warm red, easy on the eyes
    (6, 0xFFD98A, 0xFF7A2E),  # morning: sunrise
    (10, 0xF0F8FF, 0x3C9BFF),  # day: cool white to blue
    (17, 0xFFB8E8, 0x8A5CFF),  # evening: pink to violet
    (22, 0xFF6A3D, 0xA0200A),
    (24, 0xFF6A3D, 0xA0200A),
)
ROWS = font.BIG_HEIGHT
DIGIT = 1  # palette 1..16: one color per digit row, top to bottom
COLON, DATE, BAR, HEAD = 17, 18, 19, 20
TOP = 2  # y of the digits
DATE_Y = 21


def theme(hour):
    for i in range(len(THEMES) - 1):
        start, top, bottom = THEMES[i]
        end, next_top, next_bottom = THEMES[i + 1]
        if start <= hour < end:
            t = max(0.0, hour - (end - 1))
            return gfx.mix(top, next_top, t), gfx.mix(bottom, next_bottom, t)
    return THEMES[0][1], THEMES[0][2]


class Scene:
    def __init__(self, group, settings):
        self.bitmap, self.pal = gfx.canvas(group, [0] * 21)
        self.pal[DATE] = 0x8C96A8
        self.minute = -1  # anything that is not a real minute, so the first frame draws everything
        self.day = -1
        self.second = None
        self.fraction = 0.0
        self.colon_x = 31

    def draw_time(self, local):
        bitmaptools.fill_region(self.bitmap, 0, 0, 64, DATE_Y - 1, 0)
        if local is None:
            text = "--:--"
        else:
            text = "%d:%02d" % (local.tm_hour, local.tm_min)
        widths = [font.glyph(c, font.BIG)[0] for c in text]
        gaps = [4 if ":" in (a, b) else 2 for a, b in zip(text, text[1:])]
        x = (64 - sum(widths) - sum(gaps)) // 2
        for i, c in enumerate(text):
            if c == ":":
                self.colon_x = x
                gfx.draw_text(self.bitmap, c, x, TOP, COLON, font.BIG)
            else:
                gfx.draw_text(self.bitmap, c, x, TOP, lambda px, py: DIGIT + py - TOP, font.BIG)
            x += widths[i] + (gaps[i] if i < len(gaps) else 0)

    def draw_date(self, local):
        bitmaptools.fill_region(self.bitmap, 0, DATE_Y, 64, 31, 0)
        if local is None:
            text = "Zeit kommt"
        else:
            text = "%s %d. %s" % (clock.WEEKDAYS[local.tm_wday], local.tm_mday, clock.MONTHS[local.tm_mon - 1])
        x = (64 - gfx.text_width(text)) // 2
        gfx.draw_text(self.bitmap, text, x, DATE_Y, DATE)

    def colors(self, local):
        hour = local.tm_hour + local.tm_min / 60 if local else 12
        top, bottom = theme(hour)
        for row in range(ROWS):
            self.pal[DIGIT + row] = gfx.mix(top, bottom, row / (ROWS - 1))
        self.top = top
        self.pal[BAR] = gfx.scale(bottom, 0.6)
        self.pal[HEAD] = top

    def frame(self, dt):
        local = clock.now()
        minute = (local.tm_hour, local.tm_min) if local else None
        if minute != self.minute:
            self.minute = minute
            self.draw_time(local)
            self.colors(local)
        day = local.tm_mday if local else None
        if day != self.day:
            self.day = day
            self.draw_date(local)

        second = local.tm_sec if local else 0
        if second != self.second:
            self.second = second
            self.fraction = 0.0
        else:
            self.fraction = min(0.999, self.fraction + dt)

        # colon: bright at the start of every second, then fading
        self.pal[COLON] = gfx.mix(self.top, gfx.scale(self.top, 0.25), 0.5 - 0.5 * math.cos(self.fraction * math.pi))

        # seconds: a line along the bottom edge with a bright head
        if local is not None:
            length = int((second + self.fraction) / 60 * 64)
            bitmaptools.fill_region(self.bitmap, 0, 31, 64, 32, 0)
            if length:
                bitmaptools.fill_region(self.bitmap, 0, 31, length, 32, BAR)
            self.bitmap[min(63, length), 31] = HEAD
