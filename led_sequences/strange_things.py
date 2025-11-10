"""
strange_things.py

Eerie red/black animation inspired by '80s sci-fi horror vibes. Uses a
slow red pulse, drifting vertical 'signal' columns that flicker, and
random static bursts to create a creepy atmosphere.

This is intentionally generic and avoids copyrighted material.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix
import random

WIDTH = 64
HEIGHT = 32

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=WIDTH, height=HEIGHT, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

# Palette: 0=black,1=dim red,2=red,3=bright (white-ish)
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 4)
palette = displayio.Palette(4)
palette[0] = 0x000000
palette[1] = 0x200000
palette[2] = 0x9A0000
palette[3] = 0xFFC8C8
t = displayio.TileGrid(bitmap, pixel_shader=palette)
g = displayio.Group()
g.append(t)
display.root_group = g

cols = [random.randint(0, HEIGHT-1) for _ in range(12)]
speeds = [random.uniform(0.02, 0.08) for _ in range(12)]
offsets = [random.uniform(0, 10) for _ in range(12)]
last = time.monotonic()

# Logo timing: show the text overlay briefly while the background animation continues
# every LOGO_INTERVAL seconds for LOGO_DURATION seconds.
LOGO_INTERVAL = 10.0
LOGO_DURATION = 3.0
last_logo = time.monotonic()
show_logo_until = 0.0

TEXT_SCALE = 3  # scale factor for the overlay text (bigger letters)

# small 5x7 font used for the overlay text
CHAR_W = 5
CHAR_H = 7
H_SP = 1
V_SP = 1
FONT = {
    'a': [0b00000,0b01110,0b00001,0b01111,0b01111],
    'b': [0b10000,0b11110,0b10001,0b10001,0b01110],
    'c': [0b00000,0b01110,0b10000,0b10000,0b01110],
    'd': [0b00001,0b01111,0b10001,0b10001,0b01111],
    'e': [0b00000,0b01110,0b10111,0b10100,0b01110],
    'f': [0b00110,0b01001,0b11111,0b01001,0b01000],
    'g': [0b00000,0b01111,0b10001,0b01111,0b00001],
    'h': [0b10000,0b11110,0b10001,0b10001,0b10001],
    'i': [0b00100,0b00000,0b01100,0b00100,0b01110],
    'j': [0b00010,0b00000,0b00010,0b10010,0b01100],
    'k': [0b10000,0b10010,0b11100,0b10110,0b10010],
    'l': [0b01100,0b00100,0b00100,0b00100,0b01110],
    'm': [0b00000,0b11010,0b10101,0b10101,0b10101],
    'n': [0b00000,0b11110,0b10001,0b10001,0b10001],
    'o': [0b00000,0b01110,0b10001,0b10001,0b01110],
    'p': [0b00000,0b11110,0b10001,0b11110,0b10000],
    'q': [0b00000,0b01111,0b10001,0b01111,0b00001],
    'r': [0b00000,0b10110,0b11001,0b10000,0b10000],
    's': [0b00000,0b01111,0b10000,0b01110,0b11110],
    't': [0b01000,0b11111,0b01000,0b01000,0b00110],
    'u': [0b00000,0b10001,0b10001,0b10011,0b01101],
    'v': [0b00000,0b10001,0b10001,0b01010,0b00100],
    'w': [0b00000,0b10001,0b10101,0b10101,0b01010],
    'x': [0b00000,0b10001,0b01110,0b01110,0b10001],
    'y': [0b00000,0b10001,0b01111,0b00001,0b01110],
    'z': [0b00000,0b11111,0b00110,0b01100,0b11111],
    '-': [0b00000,0b00000,0b01110,0b00000,0b00000],
    '_': [0b00000,0b00000,0b00000,0b00000,0b11111],
    ' ': [0b00000,0b00000,0b00000,0b00000,0b00000],
}

def clear():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

def pulse(t0):
    # slow breathing between 0.5..1.0 brightness factor
    import math
    return 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t0 * 0.8))

print("Starting 'strange_things' animation. Press RESET to stop.")
while True:
    now = time.monotonic()
    dt = now - last
    last = now

    # base black
    clear()

    # red pulse background
    p = pulse(now)
    bg_level = 1 if p < 0.7 else 2
    # fill a subtle gradient-ish background by setting every other pixel
    for y in range(HEIGHT):
        for x in range(0, WIDTH, 2):
            bitmap[x, y] = bg_level

    # drifting vertical signal columns
    for i in range(len(cols)):
        offsets[i] += speeds[i]
        x = (i * 5 + int(offsets[i]*1.3)) % WIDTH
        # column height wiggles
        h = int(4 + 10 * (0.5 + 0.5 * random.random()))
        top = random.randint(0, HEIGHT - h)
        for yy in range(top, min(HEIGHT, top + h)):
            # flicker: occasionally bright
            if random.random() < 0.07:
                bitmap[x, yy] = 3
            else:
                bitmap[x, yy] = 2
            # slight spread
            if x+1 < WIDTH and random.random() < 0.35:
                bitmap[x+1, yy] = 2
            if x-1 >= 0 and random.random() < 0.25:
                bitmap[x-1, yy] = 1

    # random static bursts
    if random.random() < 0.06:
        sx = random.randint(0, WIDTH-8)
        sy = random.randint(0, HEIGHT-6)
        for ry in range(sy, sy + random.randint(2, 6)):
            for rx in range(sx, sx + random.randint(3, 8)):
                bitmap[rx, ry] = random.choice((1,2,3))

    # occasional vertical scan line flash
    if random.random() < 0.02:
        sx = random.randint(0, WIDTH-1)
        for yy in range(HEIGHT):
            bitmap[sx, yy] = 3 if random.random() < 0.3 else 2

    # decide whether to start a logo show
    if (now - last_logo) >= LOGO_INTERVAL:
        show_logo_until = now + LOGO_DURATION
        last_logo = now

    # If within the logo window, draw the overlay text on top
    if now <= show_logo_until:
        # simple centered two-line text: "stranger" then "things"
        def draw_overlay_text(x, y, text, color_idx=3, scale=TEXT_SCALE):
            # draw scaled pixels for each char using the same small FONT
            cx = x
            for ch in text:
                pattern = FONT.get(ch.lower(), None)
                if not pattern:
                    cx += (CHAR_W + H_SP) * scale
                    continue
                for col_idx in range(len(pattern)):
                    col = pattern[col_idx]
                    for bit in range(CHAR_H):
                        if (col >> bit) & 1:
                            # fill a scale x scale block
                            for sx in range(scale):
                                for sy in range(scale):
                                    px = cx + col_idx * scale + sx
                                    py = y + bit * scale + sy
                                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                                        bitmap[px, py] = color_idx
                cx += (CHAR_W + H_SP) * scale

        # compute centered positions
        line1 = "stranger"
        line2 = "things"
        # estimate widths
        w1 = len(line1) * (CHAR_W + H_SP) * TEXT_SCALE
        w2 = len(line2) * (CHAR_W + H_SP) * TEXT_SCALE
        x1 = max(0, (WIDTH - w1) // 2)
        x2 = max(0, (WIDTH - w2) // 2)
        y1 = 4
        y2 = y1 + (CHAR_H + V_SP) * TEXT_SCALE + 2

        # draw slight shadow for logo depth
        draw_overlay_text(x1+1, y1+1, line1, color_idx=1, scale=TEXT_SCALE)
        draw_overlay_text(x2+1, y2+1, line2, color_idx=1, scale=TEXT_SCALE)
        draw_overlay_text(x1, y1, line1, color_idx=3, scale=TEXT_SCALE)
        draw_overlay_text(x2, y2, line2, color_idx=3, scale=TEXT_SCALE)

    time.sleep(0.04)
