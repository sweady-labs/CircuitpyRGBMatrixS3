"""
menu.py - readable menu for 64x32 matrix

This file provides a simple readable on-screen menu. It prefers using the
built-in `terminalio` + `adafruit_display_text.label` if available (clean,
antialiased text). If those libraries aren't available it falls back to a
dependency-free scaled 5x7 pixel renderer.

Controls: UP/DOWN to move, pair-press to select immediately, or long-press to
select. Selection is saved to `microcontroller.nvm[0]` and the board soft-reloads.
"""

import time
import board
import displayio
import framebufferio
import rgbmatrix
import keypad
import microcontroller
import supervisor

# Try to use terminalio + adafruit_display_text.label for clearer text when available
use_label = False
try:
    import terminalio
    from adafruit_display_text import label as adalabel
    use_label = True
except Exception:
    use_label = False

ANIMATIONS = [
    "bouncing_balls",
    "breathing",
    "cap-shield",
    "dna",
    "fireworks",
    "game_of_life",
    "ironman",
    "kaleidoscope",
    "matrix_rain",
    "moving-lines",
    "plasma",
    "rain",
    "scrolling_text",
    "warp",
    "strange_things",
    "christmas",
    "tetris",
]

WIDTH = 64
HEIGHT = 32

# 5x7 font (columns of 7 bits, LSB is top row)
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

# Setup display
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=WIDTH, height=HEIGHT, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
              board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

# Bitmap with 3 color indices: bg=0, fg=1, highlight=2
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 3)
palette = displayio.Palette(3)
palette[0] = 0x000000
palette[1] = 0x80FF80
palette[2] = 0xFFFF00
tg = displayio.TileGrid(bitmap, pixel_shader=palette)
g = displayio.Group()
g.append(tg)
display.root_group = g

# Rendering helpers for 5x7 font
CHAR_W = 5
CHAR_H = 7
H_SP = 1
V_SP = 1
# Scale factor for readability: each font pixel becomes SCALE x SCALE block
SCALE = 2

def clear_bitmap():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

def draw_char(x, y, ch, color_index=1):
    ch = ch.lower()
    pattern = FONT.get(ch)
    if not pattern:
        return
    for cx in range(len(pattern)):
        col = pattern[cx]
        for ry in range(CHAR_H):
            if (col >> ry) & 1:
                # draw a SCALE x SCALE block for readability
                for sx in range(SCALE):
                    for sy in range(SCALE):
                        px = x + cx * SCALE + sx
                        py = y + ry * SCALE + sy
                        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                            bitmap[px, py] = color_index

def draw_text(x, y, text, color_index=1, max_width=None):
    if max_width is None:
        max_width = WIDTH - x
    cx = x
    scaled_char_advance = CHAR_W * SCALE + H_SP * SCALE
    for ch in text:
        if cx + scaled_char_advance > x + max_width:
            break
        draw_char(cx, y, ch, color_index)
        cx += scaled_char_advance

# Menu layout
WINDOW = 3
# compute scaled line y positions
LINE_Y = [1, 1 + (CHAR_H * SCALE + V_SP * SCALE) * 1, 1 + (CHAR_H * SCALE + V_SP * SCALE) * 2]
sel = 0

# Input handling
buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)
pressed = set()
press_time = {}
LONG_PRESS_SECONDS = 1.0
PAIR_WINDOW = 0.18
NAV_DEBOUNCE = 0.12
last_nav = 0
pending_nav = None
both_pressed_since = None

# If terminal label is available, create persistent labels (easier to read)
item_labels = None
if use_label:
    item_labels = []
    for i in range(WINDOW):
        lbl = adalabel.Label(terminalio.FONT, text="", color=0x80FF80)
        lbl.x = 4
        lbl.y = 4 + i * 10
        g.append(lbl)
        item_labels.append(lbl)

def render():
    clear_bitmap()
    start = max(0, min(sel - 1, len(ANIMATIONS) - WINDOW))
    if use_label and item_labels is not None:
        for i in range(WINDOW):
            idx = start + i
            if idx < len(ANIMATIONS):
                item_labels[i].text = ANIMATIONS[idx].replace('_', '-')
                item_labels[i].color = 0xFFFF00 if idx == sel else 0x80FF80
            else:
                item_labels[i].text = ""
    else:
        # limit chars to fit scaled display: adjust if you want fewer/more chars
        max_chars = 8
        for i in range(WINDOW):
            idx = start + i
            if idx < len(ANIMATIONS):
                name = ANIMATIONS[idx]
                color = 2 if idx == sel else 1
                draw_text(2, LINE_Y[i], name.replace('_', '-')[:max_chars], color_index=color, max_width=WIDTH-4)

render()
print("Menu running: using terminalio label" if use_label else "Menu running: using built-in pixel renderer")
print("Use UP/DOWN to move, pair-press or long-press to select.")

while True:
    now = time.monotonic()
    event = buttons.events.get()
    if event:
        if event.pressed:
            pressed.add(event.key_number)
            press_time[event.key_number] = now
            if pending_nav is not None and pending_nav[0] != event.key_number and (now - pending_nav[1]) <= PAIR_WINDOW:
                # immediate selection on pair-press
                pending_nav = None
                print(f"Selected (pair-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.12)
                supervisor.reload()
            else:
                pending_nav = (event.key_number, now)
        else:
            if event.key_number in pressed:
                pressed.remove(event.key_number)
            start_t = press_time.pop(event.key_number, None)
            if start_t is not None and (now - start_t) >= LONG_PRESS_SECONDS:
                print(f"Selected (long-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.12)
                supervisor.reload()

    if 0 in pressed and 1 in pressed:
        if both_pressed_since is None:
            both_pressed_since = now
        elif (now - both_pressed_since) >= LONG_PRESS_SECONDS:
            print(f"Selected (both long-press): {ANIMATIONS[sel]}")
            microcontroller.nvm[0] = sel
            time.sleep(0.12)
            supervisor.reload()

    if pending_nav is not None and (now - pending_nav[1]) > PAIR_WINDOW:
        key, t = pending_nav
        if now - last_nav > NAV_DEBOUNCE:
            if key == 0:
                sel = (sel - 1) % len(ANIMATIONS)
                render()
                last_nav = now
            elif key == 1:
                sel = (sel + 1) % len(ANIMATIONS)
                render()
                last_nav = now
        pending_nav = None

    time.sleep(0.03)
"""
menu.py - compact 5x7 pixel-font menu (with optional bitmap BDF for crisper text)

This file renders a small 5x7 pixel font directly into a displayio.Bitmap so it
doesn't require external libraries. If a BDF is present at /lib/fonts/5x7.bdf
and the `adafruit_bitmap_font` + `adafruit_display_text.bitmap_label` libs are
available, it will optionally create persistent bitmap_label.Label objects for
sharper text and reduced flicker.

Controls: UP/DOWN to move, pair-press to select immediately, or long-press to
select. Selection is saved to microcontroller.nvm[0] and the board soft-reloads.
"""


render()
if lbls:
    print("Menu running: using bitmap_label (BDF)")
else:
    print("Menu running: using built-in pixel renderer")
print("Use UP/DOWN to move, pair-press or long-press to select.")

while True:
    now = time.monotonic()
    event = buttons.events.get()
    if event:
        if event.pressed:
            pressed.add(event.key_number)
            press_time[event.key_number] = now
            if pending_nav is not None and pending_nav[0] != event.key_number and (now - pending_nav[1]) <= PAIR_WINDOW:
                # immediate selection on pair-press
                pending_nav = None
                print(f"Selected (pair-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.12)
                supervisor.reload()
            else:
                pending_nav = (event.key_number, now)
        else:
            if event.key_number in pressed:
                pressed.remove(event.key_number)
            start_t = press_time.pop(event.key_number, None)
            if start_t is not None and (now - start_t) >= LONG_PRESS_SECONDS:
                print(f"Selected (long-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.12)
                supervisor.reload()

    if 0 in pressed and 1 in pressed:
        if both_pressed_since is None:
            both_pressed_since = now
        elif (now - both_pressed_since) >= LONG_PRESS_SECONDS:
            print(f"Selected (both long-press): {ANIMATIONS[sel]}")
            microcontroller.nvm[0] = sel
            time.sleep(0.12)
            supervisor.reload()

    if pending_nav is not None and (now - pending_nav[1]) > PAIR_WINDOW:
        key, t = pending_nav
        if now - last_nav > NAV_DEBOUNCE:
            if key == 0:
                sel = (sel - 1) % len(ANIMATIONS)
                render()
                last_nav = now
            elif key == 1:
                sel = (sel + 1) % len(ANIMATIONS)
                render()
                last_nav = now
        pending_nav = None

    time.sleep(0.03)
"""
menu.py - text menu to choose an animation

Run this from `code.py` (it will call this when you hold both UP+DOWN during boot,
or you can run it directly). Use UP/DOWN to move, press BOTH buttons to select,
or long-press either button to select.
This version shows a small sliding window so text fits a 64x32 matrix and uses
local press tracking so selection works reliably across CircuitPython builds.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import label
import keypad
import microcontroller
import supervisor

ANIMATIONS = [
    "bouncing_balls",
    "breathing",
    "cap-shield",
    "dna",
    "fireworks",
    "game_of_life",
    "ironman",
    "kaleidoscope",
    "matrix_rain",
    "moving-lines",
    "plasma",
    "rain",
    "scrolling_text",
    "warp",
]

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

group = displayio.Group()
display.root_group = group

# We'll display a small sliding window of items so the text fits the 64x32 matrix.
WINDOW = 3
item_labels = [label.Label(terminalio.FONT, text="", color=0x80FF80) for _ in range(WINDOW)]
for i, l in enumerate(item_labels):
    l.x = 4
    # tighter vertical spacing to fit more text on 64x32
    l.y = 4 + (i * 9)
    group.append(l)

sel = 0
def refresh():
    # compute window start so sel is centered when possible
    start = max(0, min(sel - 1, len(ANIMATIONS) - WINDOW))
    for i in range(WINDOW):
        idx = start + i
        if idx < len(ANIMATIONS):
            item_labels[i].text = ANIMATIONS[idx]
            item_labels[i].color = 0xFFFF00 if idx == sel else 0x80FF80
        else:
            item_labels[i].text = ""

refresh()

buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)

print("Menu running. Use UP/DOWN to move, press BOTH (or long-press) to select.")

# Track pressed state and press times locally for reliable detection.
# To avoid rapid toggling when the user presses both buttons roughly
# simultaneously, we wait a short WINDOW for a second press before
# treating a single press as navigation. If both buttons are held for
# LONG_PRESS_SECONDS we trigger selection.
pressed = set()
press_time = {}
LONG_PRESS_SECONDS = 1.0
# when the first button is pressed, wait this long for a second press
PAIR_WINDOW = 0.18
# short debounce for navigation
NAV_DEBOUNCE = 0.12
last_nav = 0

# pending navigation: (key_number, time_pressed) waiting to be confirmed
pending_nav = None
# when both become pressed, record when that started
both_pressed_since = None

while True:
    now = time.monotonic()
    event = buttons.events.get()
    if event:
        # update pressed set and timestamps
        if event.pressed:
            pressed.add(event.key_number)
            press_time[event.key_number] = now
            # If there's already a pending_nav for the other key and it's
            # within the PAIR_WINDOW, cancel pending_nav and start both-press
            if pending_nav is not None and pending_nav[0] != event.key_number and (now - pending_nav[1]) <= PAIR_WINDOW:
                # Detected a near-simultaneous second press -> treat as immediate selection
                pending_nav = None
                print(f"Selected (pair-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.15)
                supervisor.reload()
            else:
                # start a pending nav for this key; we'll confirm it after PAIR_WINDOW
                pending_nav = (event.key_number, now)
        else:
            # release
            if event.key_number in pressed:
                pressed.remove(event.key_number)
            start_t = press_time.pop(event.key_number, None)
            # if this release ends a both-press, clear both_pressed_since
            if both_pressed_since is not None and not (0 in pressed and 1 in pressed):
                both_pressed_since = None
            # detect long-press on release as selection
            if start_t is not None and (now - start_t) >= LONG_PRESS_SECONDS:
                print(f"Selected (long-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.2)
                supervisor.reload()

    # If both are currently pressed, and both_pressed_since was set by the
    # pairing logic, check for long-press selection.
    if 0 in pressed and 1 in pressed:
        if both_pressed_since is None:
            # they became both-pressed without the pairing flow (unlikely), set start
            both_pressed_since = now
        elif (now - both_pressed_since) >= LONG_PRESS_SECONDS:
            print(f"Selected (both long-press): {ANIMATIONS[sel]}")
            microcontroller.nvm[0] = sel
            time.sleep(0.2)
            supervisor.reload()

    # If there's a pending_nav and the PAIR_WINDOW elapsed without a second
    # press, perform navigation now (but obey debounce).
    if pending_nav is not None and (now - pending_nav[1]) > PAIR_WINDOW:
        key, t = pending_nav
        if now - last_nav > NAV_DEBOUNCE:
            if key == 0:
                sel = (sel - 1) % len(ANIMATIONS)
                refresh()
                last_nav = now
            elif key == 1:
                sel = (sel + 1) % len(ANIMATIONS)
                refresh()
                last_nav = now
        pending_nav = None

    time.sleep(0.03)
"""
menu.py - text menu to choose an animation

Run this from `code.py` (it will call this when you hold both UP+DOWN during boot,
or you can run it directly). Use UP/DOWN to move, press BOTH buttons to select,
or long-press either button to select.
This version shows a small sliding window so text fits a 64x32 matrix and uses
local press tracking so selection works reliably across CircuitPython builds.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import label
import keypad
import microcontroller
import supervisor

ANIMATIONS = [
    "bouncing_balls",
    "breathing",
    "cap-shield",
    "dna",
    "fireworks",
    "game_of_life",
    "ironman",
    "kaleidoscope",
    "matrix_rain",
    "moving-lines",
    "plasma",
    "rain",
    "scrolling_text",
    "warp",
]

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

group = displayio.Group()
display.root_group = group

# We'll display a small sliding window of items so the text fits the 64x32 matrix.
WINDOW = 3
item_labels = [label.Label(terminalio.FONT, text="", color=0x80FF80) for _ in range(WINDOW)]
for i, l in enumerate(item_labels):
    l.x = 4
    # tighter vertical spacing to fit more text on 64x32
    l.y = 4 + (i * 9)
    group.append(l)

sel = 0
def refresh():
    # compute window start so sel is centered when possible
    start = max(0, min(sel - 1, len(ANIMATIONS) - WINDOW))
    for i in range(WINDOW):
        idx = start + i
        if idx < len(ANIMATIONS):
            item_labels[i].text = ANIMATIONS[idx]
            item_labels[i].color = 0xFFFF00 if idx == sel else 0x80FF80
        else:
            item_labels[i].text = ""

refresh()

buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)

print("Menu running. Use UP/DOWN to move, press BOTH (or long-press) to select.")

# Track pressed state and press times locally for reliable detection.
# To avoid rapid toggling when the user presses both buttons roughly
# simultaneously, we wait a short WINDOW for a second press before
# treating a single press as navigation. If both buttons are held for
# LONG_PRESS_SECONDS we trigger selection.
pressed = set()
press_time = {}
LONG_PRESS_SECONDS = 1.0
# when the first button is pressed, wait this long for a second press
PAIR_WINDOW = 0.18
# short debounce for navigation
NAV_DEBOUNCE = 0.12
last_nav = 0

# pending navigation: (key_number, time_pressed) waiting to be confirmed
pending_nav = None
# when both become pressed, record when that started
both_pressed_since = None

while True:
    now = time.monotonic()
    event = buttons.events.get()
    if event:
        # update pressed set and timestamps
        if event.pressed:
            pressed.add(event.key_number)
            press_time[event.key_number] = now
            # If there's already a pending_nav for the other key and it's
            # within the PAIR_WINDOW, cancel pending_nav and start both-press
            if pending_nav is not None and pending_nav[0] != event.key_number and (now - pending_nav[1]) <= PAIR_WINDOW:
                pending_nav = None
                both_pressed_since = now
            else:
                # start a pending nav for this key; we'll confirm it after PAIR_WINDOW
                pending_nav = (event.key_number, now)
        else:
            # release
            if event.key_number in pressed:
                pressed.remove(event.key_number)
            start_t = press_time.pop(event.key_number, None)
            # if this release ends a both-press, clear both_pressed_since
            if both_pressed_since is not None and not (0 in pressed and 1 in pressed):
                both_pressed_since = None
            # detect long-press on release as selection
            if start_t is not None and (now - start_t) >= LONG_PRESS_SECONDS:
                print(f"Selected (long-press): {ANIMATIONS[sel]}")
                microcontroller.nvm[0] = sel
                time.sleep(0.2)
                supervisor.reload()

    # If both are currently pressed, and both_pressed_since was set by the
    # pairing logic, check for long-press selection.
    if 0 in pressed and 1 in pressed:
        if both_pressed_since is None:
            # they became both-pressed without the pairing flow (unlikely), set start
            both_pressed_since = now
        elif (now - both_pressed_since) >= LONG_PRESS_SECONDS:
            print(f"Selected (both long-press): {ANIMATIONS[sel]}")
            microcontroller.nvm[0] = sel
            time.sleep(0.2)
            supervisor.reload()

    # If there's a pending_nav and the PAIR_WINDOW elapsed without a second
    # press, perform navigation now (but obey debounce).
    if pending_nav is not None and (now - pending_nav[1]) > PAIR_WINDOW:
        key, t = pending_nav
        if now - last_nav > NAV_DEBOUNCE:
            if key == 0:
                sel = (sel - 1) % len(ANIMATIONS)
                refresh()
                last_nav = now
            elif key == 1:
                sel = (sel + 1) % len(ANIMATIONS)
                refresh()
                last_nav = now
        pending_nav = None

    time.sleep(0.03)
"""
menu.py - text menu to choose an animation

Run this from `code.py` (it will call this when you hold both UP+DOWN during boot,
or you can run it directly). Use UP/DOWN to move, and press BOTH buttons to select.
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import label
import keypad
import microcontroller
import supervisor

ANIMATIONS = [
    "bouncing_balls",
    "breathing",
    "cap-shield",
    "dna",
    "fireworks",
    "game_of_life",
    "ironman",
    "kaleidoscope",
    "matrix_rain",
    "moving-lines",
    "plasma",
    "rain",
    "scrolling_text",
    "warp",
]

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

group = displayio.Group()
display.root_group = group

title = label.Label(terminalio.FONT, text="Animation Menu", color=0xFFFFFF)
title.x = 2
title.y = 2
group.append(title)

item_labels = []
for i, name in enumerate(ANIMATIONS):
    l = label.Label(terminalio.FONT, text=name, color=0x80FF80)
    l.x = 4
    l.y = 12 + i * 8
    item_labels.append(l)
    group.append(l)

sel = 0
def refresh():
    for i, l in enumerate(item_labels):
        if i == sel:
            l.color = 0xFFFF00
        else:
            l.color = 0x80FF80

refresh()

buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)

print("Menu running. Use UP/DOWN to move, press BOTH to select.")

while True:
    event = buttons.events.get()
    if event and event.pressed:
        if event.key_number == 0:
            sel = (sel - 1) % len(ANIMATIONS)
            refresh()
        elif event.key_number == 1:
            sel = (sel + 1) % len(ANIMATIONS)
            refresh()

    # Check for both pressed using internal state if available
    try:
        pressed_mask = buttons._pressed
    except Exception:
        pressed_mask = set()

    if 0 in pressed_mask and 1 in pressed_mask:
        print(f"Selected: {ANIMATIONS[sel]}")
        microcontroller.nvm[0] = sel
        time.sleep(0.2)
        supervisor.reload()

    time.sleep(0.05)
