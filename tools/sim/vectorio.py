"""Stand-in for CircuitPython's vectorio: Circle, Rectangle, Polygon."""
import numpy as np


class _Shape:
    def __init__(self, pixel_shader, x, y, color_index):
        self.pixel_shader = pixel_shader
        self.x = x
        self.y = y
        self.color_index = color_index
        self.hidden = False

    def _values(self, inside):
        values = np.full(inside.shape, len(self.pixel_shader.colors), dtype=np.uint32)
        values[inside] = self.color_index
        return values


class Circle(_Shape):
    def __init__(self, *, pixel_shader, radius, x=0, y=0, color_index=0):
        super().__init__(pixel_shader, x, y, color_index)
        self.radius = radius

    def mask(self):
        r = int(self.radius)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        return self._values(xx * xx + yy * yy <= r * r), int(self.x) - r, int(self.y) - r


class Rectangle(_Shape):
    def __init__(self, *, pixel_shader, width, height, x=0, y=0, color_index=0):
        super().__init__(pixel_shader, x, y, color_index)
        self.width = width
        self.height = height

    def mask(self):
        return self._values(np.ones((int(self.height), int(self.width)), dtype=bool)), int(self.x), int(self.y)


class Polygon(_Shape):
    def __init__(self, *, pixel_shader, points, x=0, y=0, color_index=0):
        super().__init__(pixel_shader, x, y, color_index)
        self.points = points

    def mask(self):
        pts = np.array(self.points, dtype=float)
        x0, y0 = int(pts[:, 0].min()), int(pts[:, 1].min())
        x1, y1 = int(pts[:, 0].max()), int(pts[:, 1].max())
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        winding = np.zeros(xx.shape, dtype=int)
        for i in range(len(pts)):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % len(pts)]
            cross = (bx - ax) * (yy - ay) - (xx - ax) * (by - ay)
            up = (ay <= yy) & (by > yy) & (cross > 0)
            down = (ay > yy) & (by <= yy) & (cross < 0)
            winding += up.astype(int) - down.astype(int)
        return self._values(winding != 0), int(self.x) + x0, int(self.y) + y0
