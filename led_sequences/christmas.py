"""
christmas.py - Christmas animation with falling snow
"""
print("Christmas starting")
import time
import random
import board
import displayio
import framebufferio
import rgbmatrix
import led_sequences.switcher as switcher

WIDTH = 64
HEIGHT = 32

try:
    print("Setting up display")
    displayio.release_displays()
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
        palette[i] = (min(255, i*2), min(255, i*2), 255)  # blue-white
    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tg)
    display.root_group = group
    print("Display setup done")
    display_ok = True
except Exception as e:
    print(f"Display setup failed: {e}")
    display_ok = False

snowflakes = []
for i in range(20):
    snowflakes.append([random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), random.uniform(0.5, 1.5)])

print("Starting animation loop")
iteration = 0
while True:
    try:
        switcher.check_switch()
        if display_ok:
            # Clear
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    bitmap[x, y] = 0
            
            # Update snowflakes
            for flake in snowflakes:
                flake[1] += flake[2]  # fall
                if flake[1] >= HEIGHT:
                    flake[1] = 0
                    flake[0] = random.randint(0, WIDTH-1)
                ix, iy = int(flake[0]), int(flake[1])
                if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                    bitmap[ix, iy] = 200  # bright white-blue
        
        time.sleep(0.05)
        iteration += 1
        if iteration % 100 == 0:
            print(f"Loop iteration {iteration}")
    except Exception as e:
        print(f"Animation error: {e}")
        time.sleep(1)