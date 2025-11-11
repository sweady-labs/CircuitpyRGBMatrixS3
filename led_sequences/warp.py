"""
warp.py
A simple "warp speed" starfield for an Adafruit RGB matrix + MatrixPortal S3.
Drops in as a separate script you can run from REPL or rename to `code.py`.

Behavior:
- Stars have (x,y,z) in normalized camera space; z decreases to simulate
  forward motion. Projection uses a focal length to create perspective.
- Each star draws a short streak from its previous projected position to the
  current one for the warp-trail effect.
- Parameters at the top let you tune star count, base speed, and brightness.

Run: save to CIRCUITPY and either `import warp` from the REPL or rename to
`code.py` to run on boot.
"""

import time
import math
import random
import board
import displayio
import framebufferio
import rgbmatrix
import led_sequences.switcher as switcher

# --- display init ---
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

bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

# palette: background dark, stars bright
palette[0] = 0x000000
palette[1] = 0x101030
palette[2] = 0x203060
palette[3] = 0x6090D0
palette[4] = 0xA0C8FF  # light blue (will join later)
palette[5] = 0xFFFFFF  # brightest head
palette[6] = 0x80FFC0  # light green (will join later)
palette[7] = 0x5080B0

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

# --- starfield params ---
NUM_STARS = 140
BASE_SPEED = 0.02   # how much z decreases per logical step
FOCAL = 24.0        # focal length for projection (tweak for depth)
MAX_STREAK = 8      # max pixels to draw for a streak

# dynamic behavior
COLOR_JOIN_DELAY = 4.0   # seconds until light blue/green start appearing
ACCEL_TIME = 3.0         # seconds to accelerate to max speed
MAX_ACCEL = 3.0          # final speed multiplier after ACCEL_TIME

# Create stars: x,y in -1..1 (camera plane), z in 0.2..1.5 (distance)
stars = []
for i in range(NUM_STARS):
    x = random.uniform(-1.0, 1.0)
    y = random.uniform(-0.6, 0.6)  # bias vertical distribution a bit
    z = random.uniform(0.2, 1.4)
    # initial color index for streak (1..7). start with blue variants
    color_idx = random.choice([1, 2])
    stars.append([x, y, z, color_idx])

# Logical timing: keep a small steady frame step and use scaled time for speed
DT = 0.03
SPEED = 3.0  # visual speed multiplier (1..6 typical)

# elapsed time to control joins/acceleration
elapsed = 0.0

# Helper: draw a short interpolated streak between (x0,y0) and (x1,y1)
def draw_streak(x0, y0, x1, y1, color_idx=1, steps_cap=MAX_STREAK):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(1, int(max(abs(dx), abs(dy))))
    if steps > MAX_STREAK:
        steps = MAX_STREAK
    for s in range(steps + 1):
        t = s / float(steps)
        px = int(round(x0 + dx * t))
        py = int(round(y0 + dy * t))
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            bitmap[px, py] = color_idx

# Main loop

while True:
    switcher.check_switch()
    # clear frame
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

    # update stars
    # update stars
    for s in stars:
        x, y, z, col = s
        # elapsed controls acceleration and color joins
        accel = 1.0 + (MAX_ACCEL - 1.0) * min(1.0, elapsed / ACCEL_TIME)
        # move star toward camera: reduce z (faster as we accelerate)
        z -= BASE_SPEED * SPEED * accel

        # if passed camera, respawn far away and possibly pick new color
        if z <= 0.02:
            x = random.uniform(-1.0, 1.0)
            y = random.uniform(-0.6, 0.6)
            z = random.uniform(0.8, 1.6)
            # before color join delay, only blue variants; after, include green/lightblue
            if elapsed < COLOR_JOIN_DELAY:
                col = random.choice([1, 2])
            else:
                col = random.choice([1, 2, 4, 6])

        # project current and previous positions
        factor = FOCAL / (z if z != 0 else 0.0001)
        px = int(round(x * factor + WIDTH / 2.0))
        py = int(round(y * factor + HEIGHT / 2.0))

        # previous position (a bit farther away) to make a streak; make streak
        # length scale with acceleration and proximity to camera for realism
        prev_z = z + BASE_SPEED * SPEED * accel * 0.9
        pf = FOCAL / (prev_z if prev_z != 0 else 0.0001)
        px0 = int(round(x * pf + WIDTH / 2.0))
        py0 = int(round(y * pf + HEIGHT / 2.0))

        # choose steps cap based on depth (nearer => longer streak)
        steps_cap = max(2, int(MAX_STREAK * (1.5 - z)))
        if steps_cap > MAX_STREAK:
            steps_cap = MAX_STREAK

        # draw streak using star's color index and a bright white head
        draw_streak(px0, py0, px, py, color_idx=col, steps_cap=steps_cap)
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            bitmap[px, py] = 5

        # write back updated star
        s[0], s[1], s[2], s[3] = x, y, z, col

    # advance elapsed time and sleep
    elapsed += DT
    time.sleep(DT)
