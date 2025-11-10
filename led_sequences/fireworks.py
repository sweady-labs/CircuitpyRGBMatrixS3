"""
fireworks.py - Particle explosions with gravity and fade
"""
import time
import random
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
palette[1] = 0x200000
palette[2] = 0x600000
palette[3] = 0xFF0000
palette[4] = 0xFF8000
palette[5] = 0xFFFF00
palette[6] = 0xFFFFFF
palette[7] = 0x8080FF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

particles = []
next_firework = 0

while True:
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if bitmap[x, y] > 0:
                bitmap[x, y] = max(0, bitmap[x, y] - 1)
    
    if next_firework <= 0:
        cx, cy = random.randint(10, WIDTH-10), random.randint(5, HEIGHT-10)
        for i in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.5)
            particles.append([cx, cy, math.cos(angle)*speed, math.sin(angle)*speed, 6])
        next_firework = random.randint(15, 40)
    
    next_firework -= 1
    
    for p in particles[:]:
        x, y, vx, vy, life = p
        vy += 0.1
        x += vx
        y += vy
        life -= 0.15
        
        if life <= 0 or x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            particles.remove(p)
        else:
            p[0], p[1], p[3], p[4] = x, y, vy, life
            ix, iy = int(x), int(y)
            if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                bitmap[ix, iy] = max(bitmap[ix, iy], int(life))
    
    time.sleep(0.04)
