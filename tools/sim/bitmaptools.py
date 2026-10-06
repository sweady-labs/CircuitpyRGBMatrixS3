"""Stand-in for CircuitPython's bitmaptools (only what the scenes use)."""
import numpy as np


def arrayblit(bitmap, data, x1=0, y1=0, x2=None, y2=None, skip_index=None):
    x2 = bitmap.width if x2 is None else x2
    y2 = bitmap.height if y2 is None else y2
    w, h = x2 - x1, y2 - y1
    values = np.asarray(data).reshape(-1)
    if values.dtype.kind == "f":
        raise TypeError("arrayblit needs integer data (use dtype=np.uint8)")
    if values.size < w * h:
        raise ValueError("data too short")
    values = values[: w * h].reshape(h, w).astype(np.int64) & bitmap._max
    target = bitmap.data[y1:y2, x1:x2]
    if skip_index is None:
        target[:] = values
    else:
        keep = values != skip_index
        target[keep] = values[keep]


def blit(dest_bitmap, source_bitmap, x, y, *, x1=0, y1=0, x2=None, y2=None, skip_source_index=None,
         skip_dest_index=None):
    x2 = source_bitmap.width if x2 is None else x2
    y2 = source_bitmap.height if y2 is None else y2
    src = source_bitmap.data[y1:y2, x1:x2]
    h, w = src.shape
    dx0, dy0 = max(0, x), max(0, y)
    dx1, dy1 = min(dest_bitmap.width, x + w), min(dest_bitmap.height, y + h)
    if dx0 >= dx1 or dy0 >= dy1:
        return
    part = src[dy0 - y:dy1 - y, dx0 - x:dx1 - x]
    target = dest_bitmap.data[dy0:dy1, dx0:dx1]
    keep = np.ones(part.shape, dtype=bool)
    if skip_source_index is not None:
        keep &= part != skip_source_index
    if skip_dest_index is not None:
        keep &= target != skip_dest_index
    target[keep] = part[keep]


def fill_region(dest_bitmap, x1, y1, x2, y2, value):
    # like on the device: coordinates outside the bitmap are an error, not clipped
    for name, v, limit in (("x1", x1, dest_bitmap.width), ("x2", x2, dest_bitmap.width),
                           ("y1", y1, dest_bitmap.height), ("y2", y2, dest_bitmap.height)):
        if not 0 <= v <= limit:
            raise ValueError("%s must be 0-%d" % (name, limit))
    x1, x2 = sorted((int(x1), int(x2)))
    y1, y2 = sorted((int(y1), int(y2)))
    dest_bitmap.data[y1:y2, x1:x2] = value


def _plot(bitmap, x, y, value):
    if 0 <= x < bitmap.width and 0 <= y < bitmap.height:
        bitmap.data[y, x] = value


def draw_line(dest_bitmap, x1, y1, x2, y2, value):
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    dx, dy = abs(x2 - x1), -abs(y2 - y1)
    sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
    err = dx + dy
    while True:
        _plot(dest_bitmap, x1, y1, value)
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x1 += sx
        if e2 <= dx:
            err += dx
            y1 += sy


def draw_circle(dest_bitmap, x, y, radius, value):
    x, y, r = int(x), int(y), int(radius)
    px, py, err = r, 0, 1 - r
    while px >= py:
        for a, b in ((px, py), (py, px), (-py, px), (-px, py), (-px, -py), (-py, -px), (py, -px), (px, -py)):
            _plot(dest_bitmap, x + a, y + b, value)
        py += 1
        if err < 0:
            err += 2 * py + 1
        else:
            px -= 1
            err += 2 * (py - px) + 1


def draw_polygon(dest_bitmap, xs, ys, value, close=True):
    if isinstance(xs, (list, tuple)) or isinstance(ys, (list, tuple)):
        raise TypeError("object with buffer protocol required (use array.array)")
    n = len(xs)
    for i in range(n - (0 if close else 1)):
        draw_line(dest_bitmap, xs[i], ys[i], xs[(i + 1) % n], ys[(i + 1) % n], value)


def boundary_fill(dest_bitmap, x, y, fill_color_value, replaced_color_value=None):
    data = dest_bitmap.data
    old = data[y, x] if replaced_color_value is None else replaced_color_value
    if old == fill_color_value:
        return
    stack = [(x, y)]
    while stack:
        px, py = stack.pop()
        if 0 <= px < dest_bitmap.width and 0 <= py < dest_bitmap.height and data[py, px] == old:
            data[py, px] = fill_color_value
            stack.extend(((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)))
