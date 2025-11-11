"""
tetris.py - Tetris-inspired animation with falling blocks
"""
print("Tetris starting")
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
        palette[i] = (min(255, i*3), min(255, i*2), 0)  # yellow-green
    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tg)
    display.root_group = group
    print("Display setup done")
    display_ok = True
except Exception as e:
    print(f"Display setup failed: {e}")
    display_ok = False

blocks = []
colors = [50, 100, 150, 200]  # different shades

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
            
            # Add new block occasionally
            if random.random() < 0.1 and len(blocks) < 10:
                blocks.append([random.randint(0, WIDTH-4), 0, random.choice(colors), random.randint(2, 4)])
            
            # Update blocks
            new_blocks = []
            for block in blocks:
                block[1] += 1  # fall
                if block[1] + block[3] < HEIGHT:
                    new_blocks.append(block)
                # Draw block
                for bx in range(block[3]):
                    for by in range(block[3]):
                        ix, iy = block[0] + bx, block[1] + by
                        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                            bitmap[ix, iy] = block[2]
            blocks = new_blocks
        
        time.sleep(0.1)
        iteration += 1
        if iteration % 100 == 0:
            print(f"Loop iteration {iteration}")
    except Exception as e:
        print(f"Animation error: {e}")
        time.sleep(1)