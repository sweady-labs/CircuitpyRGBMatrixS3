"""
matrix_rain.py - Falling green characters (Matrix style)
"""
import time
import random
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
palette[1] = 0x001000
palette[2] = 0x002000
palette[3] = 0x004000
palette[4] = 0x008000
palette[5] = 0x00C000
palette[6] = 0x00FF00
palette[7] = 0xFFFFFF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

streams = []
for x in range(WIDTH):
    if random.random() < 0.3:
        streams.append([x, random.randint(-20, 0), random.uniform(0.5, 1.2), 
                       random.randint(5, 15)])

print("[matrix_rain] Starting animation loop")

while True:
    switcher.check_switch()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if bitmap[x, y] > 0:
                bitmap[x, y] = max(0, bitmap[x, y] - 1)
    
    for s in streams:
        x, y, speed, length = s
        y += speed
        
        if y > HEIGHT + length:
            s[1] = random.randint(-20, -5)
            s[2] = random.uniform(0.5, 1.2)
            s[3] = random.randint(5, 15)
        else:
            s[1] = y
            for i in range(length):
                yy = int(y - i)
                if 0 <= yy < HEIGHT:
                    if i == 0:
                        bitmap[x, yy] = 7
                    elif i < 3:
                        bitmap[x, yy] = 6
                    else:
                        bitmap[x, yy] = max(bitmap[x, yy], 5 - i // 2)
    
    if len(streams) < WIDTH * 0.4 and random.random() < 0.1:
        x = random.randint(0, WIDTH-1)
        streams.append([x, random.randint(-10, 0), random.uniform(0.5, 1.2),
                       random.randint(5, 15)])
    
    time.sleep(0.05)
