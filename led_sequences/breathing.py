"""
breathing.py - Pulsing geometric patterns with color cycling
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
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

palette[0] = 0x000000
for i in range(1, 8):
    palette[i] = 0xFF0000

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

cx, cy = WIDTH / 2.0, HEIGHT / 2.0
t = 0.0

while True:
    switcher.check_switch()
    t += 0.08
    pulse = (math.sin(t * 1.2) + 1.0) * 0.5
    hue = (t * 0.3) % 6.0
    
    # HSV to RGB
    h = hue
    if h < 1: r, g, b = 1, h, 0
    elif h < 2: r, g, b = 2-h, 1, 0
    elif h < 3: r, g, b = 0, 1, h-2
    elif h < 4: r, g, b = 0, 4-h, 1
    elif h < 5: r, g, b = h-4, 0, 1
    else: r, g, b = 1, 0, 6-h
    
    for i in range(1, 8):
        v = i / 7.0
        palette[i] = (int(r*v*255) << 16) | (int(g*v*255) << 8) | int(b*v*255)
    
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            ring = (dist + pulse * 8) % 12
            if ring < 6:
                bitmap[x, y] = int(ring) + 1
            else:
                bitmap[x, y] = 0
    
    time.sleep(0.03)
