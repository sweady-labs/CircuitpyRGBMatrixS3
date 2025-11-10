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
    h = i / 256.0 * 6
    if h < 1: r, g, b = 255, int(h*255), 0
    elif h < 2: r, g, b = int((2-h)*255), 255, 0
    elif h < 3: r, g, b = 0, 255, int((h-2)*255)
    elif h < 4: r, g, b = 0, int((4-h)*255), 255
    elif h < 5: r, g, b = int((h-4)*255), 0, 255
    else: r, g, b = 255, 0, int((6-h)*255)
    palette[i] = (r << 16) | (g << 8) | b

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

cx, cy = WIDTH / 2.0, HEIGHT / 2.0
t = 0.0

while True:
    t += 0.06
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx, dy = x - cx, y - cy
            angle = math.atan2(dy, dx) + t
            dist = math.sqrt(dx*dx + dy*dy)
            
            mirror_angle = angle % (math.pi / 3)
            v = math.sin(mirror_angle * 6 + dist * 0.3 - t * 2) * 0.5 + 0.5
            v += math.sin(dist * 0.2 + t) * 0.3
            
            bitmap[x, y] = int((v * 0.7 + 0.15) * 255) % 256
    
    time.sleep(0.03)
