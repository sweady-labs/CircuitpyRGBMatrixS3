import time
import math
import board
import displayio
import framebufferio
import rgbmatrix

# Provide hypot fallback for CircuitPython builds without math.hypot
try:
    hypot = math.hypot
except Exception:
    import math as _math
    def hypot(dx, dy):
        return _math.sqrt(dx*dx + dy*dy)

# --- Setup Display ---
displayio.release_displays()

WIDTH = 64
HEIGHT = 32
USE_ADDR_E = False  # set True for 64x64 panels

addr_pins = [
    board.MTX_ADDRA,
    board.MTX_ADDRB,
    board.MTX_ADDRC,
    board.MTX_ADDRD,
]
if USE_ADDR_E:
    addr_pins.append(board.MTX_ADDRE)

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=4,
    rgb_pins=[
        board.MTX_R1, board.MTX_G1, board.MTX_B1,
        board.MTX_R2, board.MTX_G2, board.MTX_B2,
    ],
    addr_pins=addr_pins,
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

# --- Colors and Layers ---
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)
palette[0] = 0x000002  # dark background
palette[1] = 0x1030FF  # blue
palette[2] = 0xFFFFFF  # white
palette[3] = 0xFF2030  # red
palette[4] = 0x101020  # inner core (dark gray)
tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

# --- Shield Geometry ---
cx = WIDTH / 2.0
cy = HEIGHT / 2.0
max_r = min(WIDTH, HEIGHT) / 2.0
r_outer = max_r * 0.95
r_mid   = max_r * 0.70
r_inner = max_r * 0.45
r_core  = max_r * 0.25

# --- Star Shape Definition ---
STAR_POINTS = 5
star_angle_step = 2 * math.pi / STAR_POINTS

def in_star(x, y, zoom, thickness=0.9):
    dx = (x - cx) * zoom
    dy = (y - cy) * zoom
    angle = math.atan2(dy, dx)
    r = hypot(dx, dy)
    a = (angle + math.pi) % (2 * math.pi)
    a = (a + star_angle_step / 2) % star_angle_step - star_angle_step / 2
    max_arm_r = r_core * 1.2
    allowed = max_arm_r * (1.0 - abs(a) / (star_angle_step / 2))
    return r < allowed * thickness

# --- Animation Loop ---
t = 0.0


def init_animation():
    """Initialize animation state"""
    return {
        "t": 0.0,
        "frame": 0,
    }

def update_animation(state):
    """Update one frame and return new state"""
    state["frame"] += 1
    t = state["t"]
    
    # advance time; increased from 0.04 -> 0.36 to make the animation ~9× faster
    t += 0.36

    # --- Smooth sinusoidal zoom (flowing, no break) ---
    zoom_speed = 0.9
    zoom = 1.2 + 0.4 * math.sin(t * zoom_speed)

    # --- Subtle breathing for rings ---
    pulse = (math.sin(t * 1.3) + 1.0) * 0.5
    pulse2 = (math.sin(t * 0.9 + 1.5) + 1.0) * 0.5
    r_outer_mod = r_outer * (0.93 + 0.05 * pulse)
    r_mid_mod   = r_mid   * (0.93 + 0.07 * pulse2)
    r_inner_mod = r_inner * (0.93 + 0.09 * (1 - pulse))

    # --- Smooth color rotation for rings (consistent mapping) ---
    def lerp(a, b, f):
        return int(a + (b - a) * f)

    def lerp_color(ca, cb, f):
        ra = (ca >> 16) & 0xFF
        ga = (ca >> 8) & 0xFF
        ba = ca & 0xFF
        rb = (cb >> 16) & 0xFF
        gb = (cb >> 8) & 0xFF
        bb = cb & 0xFF
        r = lerp(ra, rb, f)
        g = lerp(ga, gb, f)
        b = lerp(ba, bb, f)
        return (r << 16) | (g << 8) | b

    mix = (math.sin(t * 0.25 - math.pi/2) + 1.0) * 0.5
    schemeA = [0x1030FF, 0xFFFFFF, 0xFF2030]
    schemeB = [0xFF2030, 0x1030FF, 0xFFFFFF]
    for i in range(3):
        palette[1 + i] = lerp_color(schemeA[i], schemeB[i], mix)
    outer_col = 1
    mid_col = 2
    inner_col = 3

    # --- Draw Shield Frame ---
    for y in range(HEIGHT):
        dy = y - cy
        for x in range(WIDTH):
            dx = x - cx
            r = hypot(dx, dy) * zoom

            c = 0
            if r < r_outer_mod:
                c = outer_col
            if r < r_mid_mod:
                c = mid_col
            if r < r_inner_mod:
                c = inner_col
            if r < r_core * zoom:
                c = 4
            if in_star(x, y, zoom, thickness=0.95) and r < r_inner_mod:
                c = 2
            bitmap[x, y] = c

    state["t"] = t
    return state
