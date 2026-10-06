"""Stand-in for rgbmatrix."""


class RGBMatrix:
    def __init__(self, *, width, height=32, bit_depth=4, **kwargs):
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.brightness = 1.0
