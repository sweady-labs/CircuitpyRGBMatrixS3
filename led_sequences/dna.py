"""
dna.py - Rotating double helix
"""
import time
import math
import board
import displayio
import framebufferio
import rgbmatrix

displayio.release_displays()

WIDTH = 64
HEIGHT = 32

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH, height=HEIGHT, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

palette[0] = 0x000000
palette[1] = 0xFF0040
palette[2] = 0xFF4080
palette[3] = 0x40FF80
palette[4] = 0x80FFC0
palette[5] = 0xFFFF00
palette[6] = 0x8080FF
palette[7] = 0xFFFFFF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

t = 0.0
cy = HEIGHT / 2.0


def init_animation():
    """Initialize animation state"""
    return {
        "t": 0.0,
        "frame": 0,
    }

def update_animation(state):
    """Update one frame and return new state"""
    state["frame"] += 1
    t = state["t"]
    
    t += 0.12
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    for x in range(WIDTH):
        angle = x * 0.3 + t
        y1 = cy + math.sin(angle) * 10
        y2 = cy - math.sin(angle) * 10
        
        ix1, iy1 = int(x), int(y1)
        ix2, iy2 = int(x), int(y2)
        
        if 0 <= iy1 < HEIGHT:
            bitmap[ix1, iy1] = 1
        if 0 <= iy2 < HEIGHT:
            bitmap[ix2, iy2] = 3
        
        if x % 6 == 0 and abs(y1 - y2) > 2:
            steps = int(abs(y2 - y1))
            for s in range(steps):
                yy = int(y1 + (y2 - y1) * s / steps)
                if 0 <= yy < HEIGHT:
                    bitmap[ix1, yy] = 7
    
    state["t"] = t
    return state
