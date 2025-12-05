"""
bouncing_balls.py - Physics simulation with gravity and bounce
"""
import time
import random
import board
import displayio
import framebufferio
import rgbmatrix

# Display setup
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
palette[1] = 0xFF0000
palette[2] = 0x00FF00
palette[3] = 0x0000FF
palette[4] = 0xFFFF00
palette[5] = 0xFF00FF
palette[6] = 0x00FFFF
palette[7] = 0xFFFFFF

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)
display.root_group = group

# Animation setup
balls = []
for i in range(8):
    balls.append([random.uniform(2, WIDTH-2), random.uniform(2, HEIGHT-2),
                  random.uniform(-2, 2), random.uniform(-2, 2), i % 7 + 1])

GRAVITY = 0.3
BOUNCE = 0.85

# Main loop with web server integration
print("Starting animation...")


def init_animation():
    """Initialize animation state"""
    return {
        "balls": [[random.uniform(2, WIDTH-2), random.uniform(2, HEIGHT-2),
                   random.uniform(-2, 2), random.uniform(-2, 2), i % 7 + 1] for i in range(8)],
        "frame": 0,
    }

def update_animation(state):
    """Update one frame and return new state"""
    state["frame"] += 1
    balls = state["balls"]
    
    # Clear display
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    # Update and draw balls
    for ball in balls:
        x, y, vx, vy, col = ball
        vy += GRAVITY
        x += vx
        y += vy
        
        if y >= HEIGHT - 1:
            y = HEIGHT - 1
            vy = -vy * BOUNCE
        if y < 0:
            y = 0
            vy = -vy * BOUNCE
        if x >= WIDTH - 1:
            x = WIDTH - 1
            vx = -vx * BOUNCE
        if x < 0:
            x = 0
            vx = -vx * BOUNCE
        
        ball[0], ball[1], ball[2], ball[3] = x, y, vx, vy
        ix, iy = int(x), int(y)
        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
            bitmap[ix, iy] = col
    
    state["balls"] = balls
    return state
