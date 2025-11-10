"""
display_test.py

Simple display test that draws sample text using the built-in 5x7 pixel
renderer (the same renderer used by the menu). Run this from the REPL with
`import led_sequences.display_test` or temporarily copy it to `code.py`.

It helps verify that the pixel font maps to the panel correctly and that
vertical/horizontal orientation is correct.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix

WIDTH = 64
HEIGHT = 32

# Small 5x7 font (same as menu)
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

CHAR_W = 5
CHAR_H = 7
H_SP = 1

def draw_char(bitmap, x, y, ch, color_index, width, height):
    ch = ch.lower()
    pattern = FONT.get(ch)
    if not pattern:
        return
    for cx in range(len(pattern)):
        col = pattern[cx]
        for ry in range(CHAR_H):
            if (col >> ry) & 1:
                px = x + cx
                py = y + ry
                if 0 <= px < width and 0 <= py < height:
                    bitmap[px, py] = color_index

def draw_text(bitmap, x, y, text, color_index, width, height):
    cx = x
    for ch in text:
        draw_char(bitmap, cx, y, ch, color_index, width, height)
        cx += CHAR_W + H_SP

def main():
    displayio.release_displays()
    matrix = rgbmatrix.RGBMatrix(width=WIDTH, height=HEIGHT, bit_depth=4,
                                 rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
                                           board.MTX_R2, board.MTX_G2, board.MTX_B2],
                                 addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
                                 clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
    display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 3)
    palette = displayio.Palette(3)
    palette[0] = 0x000000
    palette[1] = 0xFFFFFF
    palette[2] = 0xFF0000
    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    g = displayio.Group()
    g.append(tg)
    display.root_group = g

    clear = lambda: [bitmap.__setitem__((x, y), 0) for y in range(HEIGHT) for x in range(WIDTH)]

    print("Display test: drawing sample text")
    clear()
    draw_text(bitmap, 2, 1, "abc def ghi", 1, WIDTH, HEIGHT)
    draw_text(bitmap, 2, 10, "jkl mno pqr", 1, WIDTH, HEIGHT)
    draw_text(bitmap, 2, 19, "stu vwx yz-", 2, WIDTH, HEIGHT)

    # Keep running so you can visually inspect
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
"""
display_test.py - simple fill test to verify RGB matrix display
This script fills the whole matrix with a bright color (green) so you can
confirm the panel is working and the display driver is initialized.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix

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
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
palette = displayio.Palette(2)
palette[0] = 0x000000
palette[1] = 0x00FF00

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
g = displayio.Group()
g.append(tg)
display.root_group = g

# fill with green
for y in range(HEIGHT):
    for x in range(WIDTH):
        bitmap[x, y] = 1

print("Display test: filled with green. Press Ctrl-D to reboot.")
while True:
    time.sleep(1)
