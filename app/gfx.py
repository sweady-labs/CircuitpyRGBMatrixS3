"""Drawing helpers for all scenes: palettes with brightness and gamma, colors, text.

Scenes describe colors as they should look (like on a computer screen). Pal turns them into
what the LEDs need: gamma corrected, dimmed to the current brightness and rounded to the
RGB565 steps of the matrix. When the brightness changes, all palettes of the running scene
are updated at once, so scenes never have to care about brightness.
"""
import displayio

from app import font

WIDTH = 64
HEIGHT = 32
GAMMA = 2.2

_lut5 = bytearray(256)  # red and blue have 5 bits on the matrix
_lut6 = bytearray(256)  # green has 6 bits
_palettes = []  # every Pal of the running scene


def set_brightness(level):
    """level 0.0 ... 1.0; updates all palettes of the running scene."""
    for i in range(256):
        lin = (i / 255) ** GAMMA * level
        _lut5[i] = round(lin * 31) * 255 // 31
        _lut6[i] = round(lin * 63) * 255 // 63
    for pal in _palettes:
        pal.apply()


def forget_palettes():
    """Called by the engine when a scene ends."""
    _palettes.clear()


def out(color):
    """Color as the LEDs need it (gamma, brightness)."""
    return (_lut5[color >> 16] << 16) | (_lut6[(color >> 8) & 255] << 8) | _lut5[color & 255]


class Pal:
    """A displayio.Palette that remembers the wanted colors and shows them corrected."""

    def __init__(self, colors, transparent=()):
        self.colors = list(colors)
        self.palette = displayio.Palette(len(self.colors))
        for index in transparent:
            self.palette.make_transparent(index)
        self.apply()
        _palettes.append(self)

    def __len__(self):
        return len(self.colors)

    def __getitem__(self, index):
        return self.colors[index]

    def __setitem__(self, index, color):
        self.colors[index] = color
        self.palette[index] = out(color)

    def set_all(self, colors):
        self.colors = list(colors)
        self.apply()

    def apply(self):
        palette = self.palette
        for index, color in enumerate(self.colors):
            palette[index] = out(color)


# --- Colors ---------------------------------------------------------------------------


def rgb(r, g, b):
    return (int(r) << 16) | (int(g) << 8) | int(b)


def split(color):
    return color >> 16, (color >> 8) & 255, color & 255


def hsv(h, s=1.0, v=1.0):
    """h, s, v from 0 to 1 (h wraps around)."""
    h = (h % 1.0) * 6.0
    i = int(h)
    f = h - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
    return rgb(r * 255, g * 255, b * 255)


def mix(a, b, t):
    """Blend from color a to color b, t from 0 to 1."""
    ar, ag, ab = split(a)
    br, bg, bb = split(b)
    return rgb(ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t)


def scale(color, factor):
    r, g, b = split(color)
    return rgb(min(255, r * factor), min(255, g * factor), min(255, b * factor))


def gradient(stops, count):
    """count colors along stops = ((0.0, color), ..., (1.0, color))."""
    colors = []
    for i in range(count):
        pos = i / (count - 1)
        for k in range(len(stops) - 1):
            p0, c0 = stops[k]
            p1, c1 = stops[k + 1]
            if pos <= p1 or k == len(stops) - 2:
                colors.append(mix(c0, c1, 0.0 if p1 == p0 else min(1.0, max(0.0, (pos - p0) / (p1 - p0)))))
                break
    return colors


# --- Layers ---------------------------------------------------------------------------


def canvas(group, colors, transparent=()):
    """Full screen bitmap with its palette, added to group. Returns (bitmap, pal)."""
    pal = Pal(colors, transparent)
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, len(colors))
    group.append(displayio.TileGrid(bitmap, pixel_shader=pal.palette))
    return bitmap, pal


def art_bitmap(rows, colors, value_count=None):
    """Bitmap from pixel art. rows: strings of equal length, one character per pixel;
    colors: character -> palette index, e.g. {".": 0, "r": 1, "w": 2}."""
    if value_count is None:
        value_count = max(colors.values()) + 1
    bitmap = displayio.Bitmap(len(rows[0]), len(rows), max(2, value_count))
    draw_art(bitmap, rows, colors, 0, 0)
    return bitmap


def draw_art(bitmap, rows, colors, x, y):
    """Draws pixel art into bitmap at x, y; index 0 is not drawn, pixels outside are skipped."""
    w, h = bitmap.width, bitmap.height
    for dy, row in enumerate(rows):
        py = y + dy
        if 0 <= py < h:
            for dx, char in enumerate(row):
                value = colors[char]
                px = x + dx
                if value and 0 <= px < w:
                    bitmap[px, py] = value


def sprite_sheet(frames, colors):
    """All frames of an animation side by side in one bitmap. Returns (sheet, width, height):
    grid = displayio.TileGrid(sheet, pixel_shader=pal.palette, tile_width=width, tile_height=height)
    grid[0] = 1  # shows frame 1, costs almost nothing"""
    width, height = len(frames[0][0]), len(frames[0])
    sheet = displayio.Bitmap(width * len(frames), height, max(2, max(colors.values()) + 1))
    for i, rows in enumerate(frames):
        draw_art(sheet, rows, colors, i * width, 0)
    return sheet, width, height


# --- Text -----------------------------------------------------------------------------


def text_width(text, table=None, spacing=1):
    if not text:
        return 0
    return sum(font.glyph(c, table)[0] for c in text) + spacing * (len(text) - 1)


def draw_text(bitmap, text, x, y, value=1, table=None, spacing=1):
    """Draws text into bitmap with pixel value value; returns the width.

    value may be a function value(px, py) -> pixel value, for gradients inside the letters.
    """
    w, h = bitmap.width, bitmap.height
    start = x
    for c in text:
        width, pixels = font.glyph(c, table)
        for gx, gy in pixels:
            px = x + gx
            py = y + gy
            if 0 <= px < w and 0 <= py < h:
                bitmap[px, py] = value(px, py) if callable(value) else value
        x += width + spacing
    return x - start - spacing


def draw_icon(bitmap, name, x, y, value=1):
    """Draws one of font.ICONS."""
    return draw_text(bitmap, (name,), x, y, value, font.ICONS)


def text_bitmap(text, table=None, spacing=1, value=1, value_count=2, height=None):
    """New bitmap that fits the text exactly (at least 1 pixel wide)."""
    if height is None:
        height = font.BIG_HEIGHT if table is font.BIG else font.NORMAL_HEIGHT
    bitmap = displayio.Bitmap(max(1, text_width(text, table, spacing)), height, value_count)
    draw_text(bitmap, text, 0, 0, value, table, spacing)
    return bitmap


class Label:
    """A line of text as its own layer: lab = Label(group, "Hallo", 0xFFAA00, x=2, y=3)."""

    def __init__(self, group, text, color, x=0, y=0, table=None, center=False):
        self.group = group
        self.table = table
        self.pal = Pal((0, color), transparent=(0,))
        self.grid = None
        self.x = x
        self.y = y
        self.center = center
        self.text = None
        self.set(text)

    def set(self, text, color=None):
        if color is not None and color != self.pal[1]:
            self.pal[1] = color
        if text == self.text:
            return
        self.text = text
        bitmap = text_bitmap(text, self.table)
        grid = displayio.TileGrid(bitmap, pixel_shader=self.pal.palette)
        grid.x = (WIDTH - bitmap.width) // 2 if self.center else self.x
        grid.y = self.y
        if self.grid is None:
            self.group.append(grid)
        else:
            self.group[self.group.index(self.grid)] = grid
        self.grid = grid
