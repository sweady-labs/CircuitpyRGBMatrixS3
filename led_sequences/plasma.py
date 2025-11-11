"""
plasma.py - Flowing colorful plasma waves
Classic demo-scene effect using sine/cosine math to create hypnotic patterns.
"""
import time
import math
import board
import displayio
import framebufferio
import rgbmatrix
import led_sequences.switcher as switcher

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

# Build rainbow palette
for i in range(256):
    if i < 85:
        r, g, b = i * 3, 255 - i * 3, 0
    elif i < 170:
        r, g, b = 255 - (i - 85) * 3, 0, (i - 85) * 3
    else:
        r, g, b = 0, (i - 170) * 3, 255 - (i - 170) * 3
    palette[i] = (r << 16) | (g << 8) | b

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

t = 0.0
while True:
    switcher.check_switch()
    
    t += 0.05
    for y in range(HEIGHT):
        for x in range(WIDTH):
            v = math.sin(x * 0.1 + t) + math.sin(y * 0.15 - t * 0.5)
            v += math.sin((x + y) * 0.08 + t * 0.3)
            v = (v + 3.0) / 6.0
            bitmap[x, y] = int(v * 255) % 256
    time.sleep(0.03)
