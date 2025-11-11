"""
strange_things.py

Eerie red/black animation inspired by '80s sci-fi horror vibes. Uses a
slow red pulse, drifting vertical 'signal' columns that flicker, and
random static bursts to create a creepy atmosphere.

This is intentionally generic and avoids copyrighted material.
"""
print("Strange things starting")
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
        palette[i] = (i, 0, 0)  # red
    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tg)
    display.root_group = group
    print("Display setup done")
    display_ok = True
except Exception as e:
    print(f"Display setup failed: {e}")
    display_ok = False

last = time.monotonic()
t = 0.0

print("Starting animation loop")
iteration = 0
while True:
    try:
        switcher.check_switch()
        now = time.monotonic()
        dt = now - last
        last = now
        t += dt
        
        if display_ok:
            # Clear
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    bitmap[x, y] = 0
            
            # Add some red static
            for i in range(50):
                x = random.randint(0, WIDTH-1)
                y = random.randint(0, HEIGHT-1)
                bitmap[x, y] = random.randint(100, 255)
        
        time.sleep(0.1)
        iteration += 1
        if iteration % 50 == 0:
            print(f"Loop iteration {iteration}")
    except Exception as e:
        print(f"Animation error: {e}")
        time.sleep(1)