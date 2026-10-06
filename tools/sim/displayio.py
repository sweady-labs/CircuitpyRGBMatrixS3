"""Stand-in for CircuitPython's displayio on a computer (only what the scenes use)."""
import numpy as np


def release_displays():
    pass


def _bits(value_count):
    bits = 1
    while (1 << bits) < value_count:
        bits *= 2
    return bits


class Bitmap:
    def __init__(self, width, height, value_count):
        if width < 1 or height < 1:
            raise ValueError("bitmap size must be at least 1x1")
        self.width = width
        self.height = height
        self._max = (1 << _bits(value_count)) - 1
        self.data = np.zeros((height, width), dtype=np.uint32)

    def _xy(self, index):
        if isinstance(index, tuple):
            x, y = index
        else:
            x, y = index % self.width, index // self.width
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("pixel coordinates out of bounds")
        return int(x), int(y)

    def __getitem__(self, index):
        x, y = self._xy(index)
        return int(self.data[y, x])

    def __setitem__(self, index, value):
        x, y = self._xy(index)
        if not 0 <= value <= self._max:
            raise ValueError("pixel value requires too many bits")
        self.data[y, x] = value

    def fill(self, value):
        if not 0 <= value <= self._max:
            raise ValueError("pixel value requires too many bits")
        self.data[:] = value


class Palette:
    def __init__(self, color_count, *, dither=False):
        self.colors = [0] * color_count
        self.transparent = [False] * color_count

    def __len__(self):
        return len(self.colors)

    def __setitem__(self, index, color):
        if isinstance(color, (tuple, list)):
            color = (int(color[0]) << 16) | (int(color[1]) << 8) | int(color[2])
        if not 0 <= color <= 0xFFFFFF:
            raise ValueError("color out of range: %r" % color)
        self.colors[index] = int(color)

    def __getitem__(self, index):
        return self.colors[index]

    def make_transparent(self, index):
        self.transparent[index] = True

    def make_opaque(self, index):
        self.transparent[index] = False

    def is_transparent(self, index):
        return self.transparent[index]


class TileGrid:
    def __init__(self, bitmap, *, pixel_shader, width=1, height=1, tile_width=None, tile_height=None,
                 default_tile=0, x=0, y=0):
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader
        self.tile_width = tile_width or bitmap.width
        self.tile_height = tile_height or bitmap.height
        self.width = width
        self.height = height
        self.tiles = np.full((height, width), default_tile, dtype=np.int32)
        self.x = x
        self.y = y
        self.hidden = False
        self.flip_x = False
        self.flip_y = False
        self.transpose_xy = False

    def __getitem__(self, index):
        x, y = index if isinstance(index, tuple) else (index % self.width, index // self.width)
        return int(self.tiles[y, x])

    def __setitem__(self, index, tile):
        x, y = index if isinstance(index, tuple) else (index % self.width, index // self.width)
        self.tiles[y, x] = tile

    def pixels(self):
        """(values, palette) of the whole grid as one array."""
        per_row = self.bitmap.width // self.tile_width
        rows = []
        for ty in range(self.height):
            row = []
            for tx in range(self.width):
                t = int(self.tiles[ty, tx])
                sx = (t % per_row) * self.tile_width
                sy = (t // per_row) * self.tile_height
                tile = self.bitmap.data[sy:sy + self.tile_height, sx:sx + self.tile_width]
                if self.flip_x:
                    tile = tile[:, ::-1]
                if self.flip_y:
                    tile = tile[::-1, :]
                if self.transpose_xy:
                    tile = tile.T
                row.append(tile)
            rows.append(np.concatenate(row, axis=1))
        return np.concatenate(rows, axis=0)


class Group:
    def __init__(self, *, scale=1, x=0, y=0):
        self.scale = scale
        self.x = x
        self.y = y
        self.hidden = False
        self._items = []

    def append(self, layer):
        if layer in self._items:
            raise ValueError("layer already in a group")
        self._items.append(layer)

    def insert(self, index, layer):
        self._items.insert(index, layer)

    def remove(self, layer):
        self._items.remove(layer)

    def pop(self, index=-1):
        return self._items.pop(index)

    def index(self, layer):
        return self._items.index(layer)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, layer):
        self._items[index] = layer

    def __iter__(self):
        return iter(self._items)


def render(group, width, height):
    """RGB picture (height, width, 3) uint8 of a group tree, as the matrix gets it."""
    import vectorio

    out = np.zeros((height, width, 3), dtype=np.uint8)

    def put(values, palette, left, top, scale):
        colors = np.array([[c >> 16, (c >> 8) & 255, c & 255] for c in palette.colors] + [[0, 0, 0]], dtype=np.uint8)
        clear = np.array(list(palette.transparent) + [True])
        idx = np.minimum(values, len(palette.colors))  # values past the palette are not drawn
        if scale != 1:
            idx = np.repeat(np.repeat(idx, scale, axis=0), scale, axis=1)
        h, w = idx.shape
        x0, y0 = max(0, left), max(0, top)
        x1, y1 = min(width, left + w), min(height, top + h)
        if x0 >= x1 or y0 >= y1:
            return
        part = idx[y0 - top:y1 - top, x0 - left:x1 - left]
        visible = ~clear[part]
        region = out[y0:y1, x0:x1]
        region[visible] = colors[part][visible]

    def walk(g, ox, oy, scale):
        if g.hidden:
            return
        s = scale * g.scale
        bx = ox + g.x * scale
        by = oy + g.y * scale
        for item in g:
            if getattr(item, "hidden", False):
                continue
            if isinstance(item, Group):
                walk(item, bx, by, s)
            elif isinstance(item, TileGrid):
                put(item.pixels(), item.pixel_shader, bx + item.x * s, by + item.y * s, s)
            elif isinstance(item, vectorio._Shape):
                values, left, top = item.mask()
                put(values, item.pixel_shader, bx + left * s, by + top * s, s)

    if group is not None:
        walk(group, 0, 0, 1)
    return out
