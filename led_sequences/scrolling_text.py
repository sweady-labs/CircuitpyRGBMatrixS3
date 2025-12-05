"""
scrolling_text.py - Smooth pixel-perfect scrolling text
"""
import time
import board
import displayio
import framebufferio
import rgbmatrix
from adafruit_display_text import label
import terminalio

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

text = "  Hello World! CircuitPython rocks!  "
text_area = label.Label(terminalio.FONT, text=text, color=0x00FF00)
text_area.x = WIDTH
text_area.y = HEIGHT // 2

group = displayio.Group()
group.append(text_area)
display.root_group = group


def init_animation():
    """Initialize animation state"""
    return {
        "x": WIDTH,
        "frame": 0,
    }

def update_animation(state):
    """Update one frame and return new state"""
    state["frame"] += 1
    x = state["x"]
    
    text_area.x = x
    x -= 1
    if x < -len(text) * 6:
        x = WIDTH
    
    state["x"] = x
    return state
