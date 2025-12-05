"""
kaleidoscope.py - Mirrored rotating patterns with color shifts
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

bitmap = displayio.Bitmap(WIDTH, HEIGHT, 256)

palette = displayio.Palette(256)
for i in range(256):
    palette[i] = (i << 16) | (i << 8) | i  # grayscale

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

cx, cy = WIDTH / 2.0, HEIGHT / 2.0
t = 0.0


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
    
    t += 0.06
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx, dy = x - cx, y - cy
            angle = math.atan2(dy, dx) + t
            dist = math.sqrt(dx*dx + dy*dy)
            if dist == 0:
                bitmap[x, y] = 0
            else:
                r = int(128 + 127 * math.sin(angle * 3))
                g = int(128 + 127 * math.sin(angle * 3 + 2))
                b = int(128 + 127 * math.sin(angle * 3 + 4))
                color = (r + g + b) // 3
                bitmap[x, y] = color % 256
    
    state["t"] = t
    return state