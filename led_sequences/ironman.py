import time
import math
import board
import displayio
import framebufferio
import rgbmatrix

# small hypot fallback
try:
    hypot = math.hypot
except Exception:
    import math as _math
    def hypot(dx, dy):
        return _math.sqrt(dx*dx + dy*dy)

# ---- display init ----
displayio.release_displays()

WIDTH = 64
HEIGHT = 32

addr_pins = [
    board.MTX_ADDRA,
    board.MTX_ADDRB,
    board.MTX_ADDRC,
    board.MTX_ADDRD,
]

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

# ---- bitmap + palette ----
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

# base (unscaled) colors
BASE_BG = 0x000000
BASE_RED = 0xC02010   # deep red
BASE_GOLD = 0xDDA000  # gold-ish faceplate
BASE_EYE = 0xFFFFFF
BASE_ACCENT = 0x802010

palette[0] = BASE_BG
# palette[1..3] will be assigned each frame with brightness scaling
palette[4] = BASE_ACCENT

# simple helpers
def scale_color(col, f):
    if f <= 0:
        return 0
    r = int(((col >> 16) & 0xFF) * f)
    g = int(((col >> 8) & 0xFF) * f)
    b = int((col & 0xFF) * f)
    r = 0 if r < 0 else (255 if r > 255 else r)
    g = 0 if g < 0 else (255 if g > 255 else g)
    b = 0 if b < 0 else (255 if b > 255 else b)
    return (r << 16) | (g << 8) | b

# tilegrid
tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

# geometry
cx = WIDTH / 2.0
cy = HEIGHT / 2.5  # slightly higher center so chin sits lower
head_rx = WIDTH * 0.42
head_ry = HEIGHT * 0.52
face_rx = head_rx * 0.7
face_ry = head_ry * 0.6

# brightness and fade
BRIGHTNESS_MAX = 0.7
FADE_TIME = 1.5

# animation loop
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
    
    # advance time (tripled speed requested by user)
    t += 2.00

    # brightness ramp
    fade = t / FADE_TIME
    if fade > 1.0:
        fade = 1.0
    bright = BRIGHTNESS_MAX * fade

    # gentle pulse to gold
    gold_pulse = 0.92 + 0.08 * (math.sin(t * 2.2) + 1.0) * 0.5

    # assign palette colors scaled
    palette[1] = scale_color(BASE_RED, bright)
    palette[2] = scale_color(int(BASE_GOLD * gold_pulse) & 0xFFFFFF, bright)
    palette[3] = scale_color(BASE_EYE, bright)

    # subtle zoom (sine-based, smooth)
    zoom = 1.0 + 0.12 * math.sin(t * 0.9)

    for y in range(HEIGHT):
        dy = y - cy
        for x in range(WIDTH):
            dx = x - cx

            # normalized coordinates
            nx = dx / head_rx
            ny = dy / head_ry

            # base head as ellipse
            head_mask = (nx*nx + ny*ny) <= 1.0

            # angular faceplate: use clipped ellipse with sloped forehead
            forehead_cut = dy < -head_ry * 0.18 and abs(dx) > head_rx * 0.35
            cheek_indent = abs(dx) > (head_rx * (0.55 + (dy / (head_ry*2.5))))

            # faceplate region roughly centered and a bit narrower
            fx = dx / (face_rx * 0.9)
            fy = (dy + head_ry*0.08) / (face_ry * 0.9)
            face_ellipse = (fx*fx + fy*fy) <= 1.0
            face_mask = face_ellipse and (not forehead_cut) and (not cheek_indent) and dy > -head_ry*0.5

            # chin taper: allow a V-shape at bottom
            chin_mask = False
            if dy > head_ry * 0.2:
                chin_mask = abs(dx) < head_rx * (0.45 - (dy - head_ry*0.2)/(head_ry*1.2))

            # eye shapes: narrow horizontal slits (two pixels wide)
            eye_y = int(cy - head_ry*0.25)
            eye_w = max(1, int(WIDTH * 0.06))
            eye_sep = int(WIDTH * 0.2)
            left_eye = (abs(x - (cx - eye_sep/2)) <= eye_w and y == eye_y)
            right_eye = (abs(x - (cx + eye_sep/2)) <= eye_w and y == eye_y)

            # highlight based on a fake light direction for a metallic sheen
            lx, ly = -0.4, -1.0
            nd = math.sqrt(dx*dx + dy*dy) + 1e-6
            lxn = (dx*lx + dy*ly) / nd
            sheen = max(0.0, min(1.0, 0.6 + 0.8 * lxn))

            c = 0
            if head_mask:
                # base red armor
                c = 1
            if face_mask:
                # gold faceplate; boost with sheen for highlights
                # pick palette index 2 for gold
                c = 2
            if chin_mask and head_mask:
                c = 1
            if (left_eye or right_eye) and face_mask:
                c = 3

            # subtle edge accents: draw darker cheek/temple areas
            if head_mask and not face_mask:
                # temple accent on sides
                if abs(dx) > head_rx * 0.55 and dy < head_ry * 0.15:
                    c = 4

            bitmap[x, y] = c

    state["t"] = t
    return state
