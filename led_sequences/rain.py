"""
rain.py - Falling rain droplets with trails
"""
import time
import random
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

palette[0] = 0x000010
palette[1] = 0x001040
palette[2] = 0x003080
palette[3] = 0x0060C0
palette[4] = 0x00A0FF
palette[5] = 0x40D0FF
palette[6] = 0x80F0FF
palette[7] = 0xFFFFFF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

drops = []
for i in range(40):
    drops.append([random.randint(0, WIDTH-1), random.randint(-10, HEIGHT-1), 
                  random.uniform(0.8, 1.5)])

while True:
    # fade trails
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if bitmap[x, y] > 0:
                bitmap[x, y] = max(0, bitmap[x, y] - 1)
    
    # update drops
    for d in drops:
        x, y, speed = d
        y += speed
        if y >= HEIGHT:
            d[0] = random.randint(0, WIDTH-1)
            d[1] = random.randint(-5, 0)
            d[2] = random.uniform(0.8, 1.5)
        else:
            d[1] = y
            ix, iy = int(x), int(y)
            if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                bitmap[ix, iy] = 7
    
    time.sleep(0.04)
