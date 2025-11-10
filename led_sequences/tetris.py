"""
tetris.py

Animated Tetris session on 64x32 matrix. Shows autonomous gameplay with:
- Classic Tetris pieces (tetrominoes) in 7 colors
- Pieces falling, rotating, and landing
- Line clearing with flash effect
- Score display
- Gradually increasing speed
- Game over and restart

This is a visual simulation (not playable) optimized for 64x32 display.
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

# Palette: 0=black, 1-7=piece colors, 8=grid, 9=white, 10=gray
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 16)
palette = displayio.Palette(16)
palette[0] = 0x000000  # black
palette[1] = 0x00FFFF  # cyan (I piece)
palette[2] = 0x0000FF  # blue (J piece)
palette[3] = 0xFF8800  # orange (L piece)
palette[4] = 0xFFFF00  # yellow (O piece)
palette[5] = 0x00FF00  # green (S piece)
palette[6] = 0x8800FF  # purple (T piece)
palette[7] = 0xFF0000  # red (Z piece)
palette[8] = 0x222222  # grid lines
palette[9] = 0xFFFFFF  # white (text/effects)
palette[10] = 0x555555 # gray (locked pieces dim)

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
g = displayio.Group()
g.append(tg)
display.root_group = g

# Tetromino shapes (relative coords for 4 blocks)
SHAPES = {
    'I': [(0,0), (1,0), (2,0), (3,0)],
    'O': [(0,0), (1,0), (0,1), (1,1)],
    'T': [(1,0), (0,1), (1,1), (2,1)],
    'S': [(1,0), (2,0), (0,1), (1,1)],
    'Z': [(0,0), (1,0), (1,1), (2,1)],
    'J': [(0,0), (0,1), (1,1), (2,1)],
    'L': [(2,0), (0,1), (1,1), (2,1)],
}

COLORS = [1, 2, 3, 4, 5, 6, 7]

# Game grid (portrait orientation: 10 wide x 30 tall to use full height)
GRID_X = 27  # center horizontally on 64px width
GRID_Y = 1
GRID_W = 10
GRID_H = 30  # taller grid for portrait mode
BLOCK_SIZE = 1  # each tetris block is 1 pixel (tight fit)

# Grid state: 0=empty, 1-7=locked piece color
grid = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]

# Current piece
current_piece = None
current_x = 0
current_y = 0
current_color = 0
current_shape = []

# Game state
score = 0
level = 1
fall_speed = 0.25  # faster: seconds per row
last_fall = time.monotonic()
game_over = False
clearing_lines = []
clear_flash_until = 0

def clear_bitmap():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

def draw_grid():
    # draw grid border
    for y in range(GRID_H):
        for x in range(GRID_W):
            px = GRID_X + x
            py = GRID_Y + y
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                # draw locked blocks
                if grid[y][x] > 0:
                    bitmap[px, py] = grid[y][x]

def draw_current_piece():
    if current_piece is None:
        return
    for (bx, by) in current_shape:
        px = GRID_X + current_x + bx
        py = GRID_Y + current_y + by
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            bitmap[px, py] = current_color

def collides(shape, x, y):
    for (bx, by) in shape:
        gx = x + bx
        gy = y + by
        if gx < 0 or gx >= GRID_W or gy >= GRID_H:
            return True
        if gy >= 0 and grid[gy][gx] > 0:
            return True
    return False

def lock_piece():
    global grid, score
    for (bx, by) in current_shape:
        gx = current_x + bx
        gy = current_y + by
        if 0 <= gy < GRID_H and 0 <= gx < GRID_W:
            grid[gy][gx] = current_color
    # check for full lines
    lines = []
    for y in range(GRID_H):
        if all(grid[y][x] > 0 for x in range(GRID_W)):
            lines.append(y)
    return lines

def clear_lines(lines):
    global grid, score
    for y in lines:
        del grid[y]
        grid.insert(0, [0 for _ in range(GRID_W)])
    score += len(lines) * 100

def spawn_piece():
    global current_piece, current_x, current_y, current_color, current_shape, game_over
    shape_name = random.choice(list(SHAPES.keys()))
    current_shape = SHAPES[shape_name]
    current_color = random.choice(COLORS)
    current_x = GRID_W // 2 - 2
    current_y = 0
    current_piece = shape_name
    if collides(current_shape, current_x, current_y):
        game_over = True

def rotate_piece():
    global current_shape
    # rotate 90 degrees clockwise
    rotated = [(by, -bx) for (bx, by) in current_shape]
    # normalize to origin
    min_x = min(bx for (bx, by) in rotated)
    min_y = min(by for (bx, by) in rotated)
    rotated = [(bx - min_x, by - min_y) for (bx, by) in rotated]
    if not collides(rotated, current_x, current_y):
        current_shape = rotated

def reset_game():
    global grid, score, level, game_over, fall_speed
    grid = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
    score = 0
    level = 1
    fall_speed = 0.25  # faster initial speed
    game_over = False
    spawn_piece()

def draw_score():
    # simple score display (left side of grid for portrait)
    # we'll just draw a vertical bar that grows with score
    bar_x = GRID_X - 2
    bar_height = min(GRID_H, score // 50)
    for i in range(bar_height):
        py = GRID_Y + GRID_H - 1 - i
        if 0 <= bar_x < WIDTH and 0 <= py < HEIGHT:
            bitmap[bar_x, py] = 4  # yellow bar

# Initialize
reset_game()
last_move = time.monotonic()
last_rotate = time.monotonic()

print("Starting Tetris animation. Press RESET to stop.")

while True:
    now = time.monotonic()
    
    clear_bitmap()
    
    if game_over:
        # flash "GAME OVER" a few times then stop (end animation)
        draw_grid()
        if int(now * 3) % 2 == 0:
            for y in range(GRID_H):
                for x in range(GRID_W):
                    px = GRID_X + x
                    py = GRID_Y + y
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        bitmap[px, py] = 9
        time.sleep(0.2)
        # after 3 seconds of game over, freeze on final grid state
        if now - last_fall > 3:
            # show final frozen grid indefinitely
            while True:
                clear_bitmap()
                draw_grid()
                time.sleep(1)
        continue
    
    # check for line clearing flash
    if clearing_lines and now < clear_flash_until:
        clear_bitmap()
        # flash the clearing lines
        if int(now * 10) % 2 == 0:
            for y in clearing_lines:
                for x in range(GRID_W):
                    px = GRID_X + x
                    py = GRID_Y + y
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        bitmap[px, py] = 9
        time.sleep(0.05)
        continue
    elif clearing_lines and now >= clear_flash_until:
        clear_lines(clearing_lines)
        clearing_lines = []
        spawn_piece()
        last_fall = now
    
    draw_grid()
    draw_current_piece()
    draw_score()
    
    # autonomous movement: random left/right and rotation (faster)
    if now - last_move > 0.08:
        move = random.choice([-1, 0, 0, 1])  # bias toward staying
        new_x = current_x + move
        if not collides(current_shape, new_x, current_y):
            current_x = new_x
        last_move = now
    
    if now - last_rotate > 0.2 and random.random() < 0.4:
        rotate_piece()
        last_rotate = now
    
    # fall
    if now - last_fall > fall_speed:
        new_y = current_y + 1
        if collides(current_shape, current_x, new_y):
            # lock piece
            lines = lock_piece()
            if lines:
                clearing_lines = lines
                clear_flash_until = now + 0.3
            else:
                spawn_piece()
        else:
            current_y = new_y
        last_fall = now
    
    # gradually increase speed (faster progression)
    fall_speed = max(0.05, 0.25 - level * 0.015)
    if score > level * 300:
        level += 1
    
    time.sleep(0.03)
