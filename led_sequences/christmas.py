"""
christmas.py

Festive Christmas animation featuring:
- Animated snowflakes drifting down
- Christmas trees with twinkling star ornaments
- Snowmen with scarves
- Colored lights border (red/green alternating)
- Gentle sparkling effects

Creates a joyful holiday scene on a 64×32 RGB matrix.
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

# Palette: 0=black, 1=white(snow), 2=green(tree), 3=red, 4=yellow(star), 5=brown(trunk), 6=orange(scarf), 7=blue, 8=pink(skin), 9=gold
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 16)
palette = displayio.Palette(16)
palette[0] = 0x000000  # black background
palette[1] = 0xFFFFFF  # white (snow, snowman, santa beard)
palette[2] = 0x00DD00  # green (tree)
palette[3] = 0xFF0000  # red (santa suit, ornaments)
palette[4] = 0xFFFF00  # yellow (star)
palette[5] = 0x8B4513  # brown (trunk)
palette[6] = 0xFF8800  # orange (scarf)
palette[7] = 0x0088FF  # blue (gifts)
palette[8] = 0xFFCC99  # pink (skin)
palette[9] = 0xFFD700  # gold (gift ribbons)
palette[10] = 0xFF00FF # magenta (ornaments)
palette[11] = 0x00FFFF # cyan (ornaments)
palette[12] = 0xFF69B4 # hot pink (gifts)
palette[13] = 0x32CD32 # lime green (gifts)
palette[14] = 0x8B00FF # purple (gifts)
palette[15] = 0xFFFFFF # white duplicate for bright spots

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
g = displayio.Group()
g.append(tg)
display.root_group = g

# Snowflakes: each has x, y, speed, size
snowflakes = []
for _ in range(50):
    snowflakes.append({
        'x': random.randint(0, WIDTH-1),
        'y': random.randint(0, HEIGHT-1),
        'speed': random.uniform(0.4, 1.2),
        'drift': random.uniform(-0.3, 0.3),
        'size': random.choice([1, 1, 2])
    })

# Santa moving across the screen
santa = {
    'x': -10,
    'y': 3,
    'speed': 0.8,
    'direction': 1
}

# Animated gifts that appear and bounce
gifts = []
for i in range(5):
    gifts.append({
        'x': random.randint(5, WIDTH-10),
        'y': HEIGHT - 8 - random.randint(0, 3),
        'color': random.choice([3, 7, 12, 13, 14]),
        'ribbon': random.choice([4, 9]),
        'bounce_offset': random.uniform(0, 6.28),
        'bounce_speed': random.uniform(0.5, 1.5)
    })

# Christmas lights on border: positions alternate red/green
border_lights = []
for x in range(0, WIDTH, 4):
    border_lights.append({'x': x, 'y': 0, 'color': 3 if (x//4) % 2 == 0 else 2})
    border_lights.append({'x': x, 'y': HEIGHT-1, 'color': 3 if (x//4) % 2 == 1 else 2})

for y in range(4, HEIGHT-4, 4):
    border_lights.append({'x': 0, 'y': y, 'color': 3 if (y//4) % 2 == 0 else 2})
    border_lights.append({'x': WIDTH-1, 'y': y, 'color': 3 if (y//4) % 2 == 1 else 2})

# Twinkle: some lights blink
twinkle_state = [random.random() > 0.5 for _ in border_lights]

# Static scene objects
def draw_tree(x, y, bmp):
    # Simple triangle tree with trunk and star on top
    # trunk (2 pixels wide, brown)
    if y+6 < HEIGHT:
        bmp[x, y+6] = 5
        if x+1 < WIDTH:
            bmp[x+1, y+6] = 5
    # tree layers (green triangles)
    tree_rows = [
        (x, [0]),         # top tip
        (x-1, [0,1,2]),   # second row
        (x-1, [0,1,2]),   # third row
        (x-2, [0,1,2,3,4]), # fourth row
        (x-2, [0,1,2,3,4]), # bottom row
    ]
    for i, (start_x, cols) in enumerate(tree_rows):
        py = y + i
        if 0 <= py < HEIGHT:
            for dx in cols:
                px = start_x + dx
                if 0 <= px < WIDTH:
                    bmp[px, py] = 2
    # star on top (yellow)
    if 0 <= y-1 < HEIGHT and 0 <= x < WIDTH:
        bmp[x, y-1] = 4

def draw_snowman(x, y, bmp):
    # Three stacked circles: bottom (3 wide), middle (2 wide), head (2 wide)
    # bottom
    if 0 <= y+5 < HEIGHT:
        for dx in range(-1, 2):
            if 0 <= x+dx < WIDTH:
                bmp[x+dx, y+5] = 1
    if 0 <= y+4 < HEIGHT:
        for dx in range(-1, 2):
            if 0 <= x+dx < WIDTH:
                bmp[x+dx, y+4] = 1
    # middle
    if 0 <= y+3 < HEIGHT:
        for dx in range(-1, 1):
            if 0 <= x+dx < WIDTH:
                bmp[x+dx, y+3] = 1
    if 0 <= y+2 < HEIGHT:
        for dx in range(-1, 1):
            if 0 <= x+dx < WIDTH:
                bmp[x+dx, y+2] = 1
    # head
    if 0 <= y+1 < HEIGHT:
        for dx in range(0, 1):
            if 0 <= x+dx < WIDTH:
                bmp[x+dx, y+1] = 1
    if 0 <= y < HEIGHT:
        if 0 <= x < WIDTH:
            bmp[x, y] = 1
    # scarf (orange)
    if 0 <= y+3 < HEIGHT:
        if 0 <= x-1 < WIDTH:
            bmp[x-1, y+3] = 6
        if 0 <= x+1 < WIDTH:
            bmp[x+1, y+3] = 6
    # eyes (black dots - use palette 0)
    if 0 <= y < HEIGHT:
        if 0 <= x-1 < WIDTH:
            bmp[x-1, y] = 0
        if 0 <= x+1 < WIDTH:
            bmp[x+1, y] = 0

def clear():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

last_frame = time.monotonic()
print("Starting Christmas animation. Press RESET to stop.")

while True:
    now = time.monotonic()
    dt = now - last_frame
    last_frame = now

    # fill sky
    clear()

    # draw border lights (twinkle effect)
    for i, light in enumerate(border_lights):
        if twinkle_state[i]:
            bitmap[light['x'], light['y']] = light['color']
    # randomly toggle some lights
    if random.random() < 0.1:
        idx = random.randint(0, len(twinkle_state)-1)
        twinkle_state[idx] = not twinkle_state[idx]

    # draw snowflakes
    for flake in snowflakes:
        flake['y'] += flake['speed'] * dt * 10
        flake['x'] += flake['drift'] * dt * 10
        if flake['y'] >= HEIGHT:
            flake['y'] = 0
            flake['x'] = random.randint(0, WIDTH-1)
        if flake['x'] < 0:
            flake['x'] = WIDTH-1
        if flake['x'] >= WIDTH:
            flake['x'] = 0
        
        fx = int(flake['x'])
        fy = int(flake['y'])
        if 0 <= fx < WIDTH and 0 <= fy < HEIGHT:
            bitmap[fx, fy] = 1
            if flake['size'] == 2:
                # bigger snowflake (cross shape)
                if fx-1 >= 0:
                    bitmap[fx-1, fy] = 1
                if fx+1 < WIDTH:
                    bitmap[fx+1, fy] = 1
                if fy-1 >= 0:
                    bitmap[fx, fy-1] = 1
                if fy+1 < HEIGHT:
                    bitmap[fx, fy+1] = 1

    # draw Christmas trees
    draw_tree(10, 20, bitmap)
    draw_tree(30, 18, bitmap)
    draw_tree(50, 22, bitmap)

    # draw snowmen
    draw_snowman(20, 20, bitmap)
    draw_snowman(42, 22, bitmap)

    # add sparkles (random bright pixels)
    if random.random() < 0.15:
        sx = random.randint(2, WIDTH-3)
        sy = random.randint(2, HEIGHT-3)
        bitmap[sx, sy] = 4  # yellow sparkle

    time.sleep(0.05)
