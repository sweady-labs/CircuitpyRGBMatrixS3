"""
game_of_life.py - Conway's Game of Life with color-coded generations
"""
import time
import random
import board
import displayio
import framebufferio
import rgbmatrix

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
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

palette[0] = 0x000000
palette[1] = 0x002000
palette[2] = 0x004000
palette[3] = 0x008000
palette[4] = 0x00C000
palette[5] = 0x00FF00
palette[6] = 0x80FF80
palette[7] = 0xFFFFFF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

grid = [[0]*HEIGHT for _ in range(WIDTH)]
for x in range(WIDTH):
    for y in range(HEIGHT):
        grid[x][y] = random.randint(0, 1)

gen = 0


def init_animation():
    """Initialize animation state"""
    return {
        "grid": [[random.randint(0, 1) for _ in range(HEIGHT)] for _ in range(WIDTH)],
        "gen": 0,
        "frame": 0,
    }

def update_animation(state):
    """Update one frame and return new state"""
    state["frame"] += 1
    grid = state["grid"]
    gen = state["gen"]
    
    new_grid = [[0]*HEIGHT for _ in range(WIDTH)]
    for x in range(WIDTH):
        for y in range(HEIGHT):
            neighbors = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = (x + dx) % WIDTH, (y + dy) % HEIGHT
                    if grid[nx][ny] > 0:
                        neighbors += 1
            
            if grid[x][y] > 0:
                new_grid[x][y] = grid[x][y] + 1 if neighbors in [2, 3] else 0
            else:
                new_grid[x][y] = 1 if neighbors == 3 else 0
            
            if new_grid[x][y] > 7:
                new_grid[x][y] = 7
    
    grid = new_grid
    for x in range(WIDTH):
        for y in range(HEIGHT):
            bitmap[x, y] = grid[x][y]
    
    gen += 1
    if gen % 100 == 0:
        for x in range(WIDTH):
            for y in range(HEIGHT):
                if random.random() < 0.05:
                    grid[x][y] = 1
    
    state["grid"] = grid
    state["gen"] = gen
    return state
