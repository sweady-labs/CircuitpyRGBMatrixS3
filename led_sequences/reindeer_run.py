"""
reindeer_run.py - Running reindeer animation for 64x32 LED matrix

Non-blocking animation featuring reindeer silhouettes galloping across
with animated antlers and starry night background.
"""
print("Reindeer Run loading")
import time
import board
import displayio
import framebufferio
import rgbmatrix

WIDTH = 64
HEIGHT = 32

# Setup display
try:
    print("Display setup")
    displayio.release_displays()
    matrix = rgbmatrix.RGBMatrix(
        width=WIDTH, height=HEIGHT, bit_depth=4,
        rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
                  board.MTX_R2, board.MTX_G2, board.MTX_B2],
        addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
        clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
    display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
    palette = displayio.Palette(8)

    # Reindeer color palette
    palette[0] = (0, 0, 20)        # dark night sky
    palette[1] = (139, 69, 19)     # brown reindeer body
    palette[2] = (205, 133, 63)    # tan reindeer highlight
    palette[3] = (220, 20, 60)     # red nose (Rudolph!)
    palette[4] = (255, 255, 255)   # white stars/antlers
    palette[5] = (100, 50, 25)     # dark brown
    palette[6] = (255, 215, 0)     # gold stars
    palette[7] = (50, 50, 50)      # gray shadow

    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tg)
    display.root_group = group
    display_ok = True
    print("Display ready")
except Exception as e:
    print("Display failed:", e)
    display_ok = False


def set_pixel(bmp, x, y, c):
    """Safely set pixel."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        bmp[x, y] = c


def draw_reindeer(bmp, x, y, leg_frame, is_rudolph=False):
    """Draw a reindeer sprite with animated legs."""
    # Body (8x5 oval)
    for dy in range(5):
        for dx in range(8):
            if (dx == 0 or dx == 7) and (dy == 0 or dy == 4):
                continue  # round corners
            set_pixel(bmp, x + dx, y + dy, 1)
    
    # Head/neck (3x4)
    for dy in range(4):
        for dx in range(3):
            set_pixel(bmp, x + 8, y + dy + 1, 1)
    
    # Nose
    nose_color = 3 if is_rudolph else 5
    set_pixel(bmp, x + 11, y + 2, nose_color)
    
    # Antlers (animated)
    antler_offset = 1 if leg_frame else 0
    set_pixel(bmp, x + 8 + antler_offset, y, 2)
    set_pixel(bmp, x + 9 + antler_offset, y - 1, 2)
    set_pixel(bmp, x + 7 + antler_offset, y - 1, 2)
    
    # Legs (animated running)
    if leg_frame:
        # Front legs forward
        set_pixel(bmp, x + 6, y + 6, 5)
        set_pixel(bmp, x + 6, y + 7, 5)
        set_pixel(bmp, x + 3, y + 5, 5)
        set_pixel(bmp, x + 3, y + 6, 5)
    else:
        # Back legs forward
        set_pixel(bmp, x + 6, y + 5, 5)
        set_pixel(bmp, x + 6, y + 6, 5)
        set_pixel(bmp, x + 3, y + 6, 5)
        set_pixel(bmp, x + 3, y + 7, 5)
    
    # Tail
    set_pixel(bmp, x - 1, y + 2, 2)


def init_animation():
    """Initialize reindeer run state."""
    # Create stars
    stars = []
    for i in range(30):
        sx = (i * 7 + 3) % WIDTH
        sy = (i * 3 + 1) % 15
        stars.append((sx, sy))
    
    return {
        "reindeer": [
            {"x": -15, "y": 18, "speed": 1.2, "rudolph": True},
            {"x": -35, "y": 20, "speed": 1.1, "rudolph": False},
            {"x": -55, "y": 16, "speed": 1.3, "rudolph": False},
        ],
        "stars": stars,
        "frame": 0,
        "star_twinkle": 0,
    }


def update_animation(state):
    """Update one frame of reindeer run animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Draw starry background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    # Draw twinkling stars
    twinkle = (state["frame"] // 10) % 3
    for sx, sy in state["stars"]:
        star_index = (sx + sy) % 3
        if star_index == twinkle:
            set_pixel(bitmap, sx, sy, 6)  # gold
        elif star_index == (twinkle + 1) % 3:
            set_pixel(bitmap, sx, sy, 4)  # white
    
    # Update and draw reindeer
    leg_frame = (state["frame"] // 5) % 2 == 0
    
    for deer in state["reindeer"]:
        deer["x"] += deer["speed"]
        
        # Wrap around
        if deer["x"] > WIDTH + 5:
            deer["x"] = -15
        
        draw_reindeer(bitmap, int(deer["x"]), deer["y"], leg_frame, deer["rudolph"])
    
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
