"""
gingerbread_dance.py - Dancing gingerbread people animation for 64x32 LED matrix

Non-blocking animation featuring cute gingerbread people doing a
synchronized dance routine with festive movements.
"""
print("Gingerbread Dance loading")
import time
import board
import displayio
import framebufferio
import rgbmatrix
import math

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
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 16)
    palette = displayio.Palette(16)

    # Gingerbread color palette
    palette[0] = (20, 0, 0)        # dark red background
    palette[1] = (139, 90, 43)     # gingerbread brown
    palette[2] = (180, 120, 60)    # light gingerbread
    palette[3] = (100, 60, 30)     # dark gingerbread
    palette[4] = (255, 255, 255)   # white icing
    palette[5] = (220, 20, 60)     # red icing/buttons
    palette[6] = (34, 139, 34)     # green icing
    palette[7] = (255, 215, 0)     # gold/yellow
    palette[8] = (255, 105, 180)   # pink icing
    palette[9] = (138, 43, 226)    # purple
    palette[10] = (255, 140, 0)    # orange
    palette[11] = (50, 0, 0)       # very dark red
    palette[12] = (255, 255, 150)  # pale yellow
    palette[13] = (200, 150, 80)   # tan
    palette[14] = (80, 40, 20)     # very dark brown
    palette[15] = (255, 200, 200)  # light pink

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


def fill_rect(bmp, x, y, w, h, c):
    """Fill rectangle."""
    for yy in range(y, min(y + h, HEIGHT)):
        for xx in range(x, min(x + w, WIDTH)):
            set_pixel(bmp, xx, yy, c)


def draw_gingerbread_person(bmp, x, y, arm_up_left, arm_up_right, leg_apart):
    """Draw a gingerbread person with animated limbs."""
    # Head (round)
    fill_rect(bmp, x + 2, y, 4, 4, 1)
    set_pixel(bmp, x + 1, y + 1, 1)
    set_pixel(bmp, x + 1, y + 2, 1)
    set_pixel(bmp, x + 6, y + 1, 1)
    set_pixel(bmp, x + 6, y + 2, 1)
    
    # Eyes (white icing)
    set_pixel(bmp, x + 3, y + 1, 4)
    set_pixel(bmp, x + 5, y + 1, 4)
    
    # Smile (red icing)
    set_pixel(bmp, x + 3, y + 3, 5)
    set_pixel(bmp, x + 4, y + 3, 5)
    
    # Body
    fill_rect(bmp, x + 2, y + 4, 4, 5, 1)
    
    # Buttons (red)
    set_pixel(bmp, x + 4, y + 5, 5)
    set_pixel(bmp, x + 4, y + 7, 5)
    
    # White icing decoration on body
    set_pixel(bmp, x + 2, y + 4, 4)
    set_pixel(bmp, x + 5, y + 4, 4)
    set_pixel(bmp, x + 2, y + 8, 4)
    set_pixel(bmp, x + 5, y + 8, 4)
    
    # Arms (animated)
    if arm_up_left:
        # Left arm up
        set_pixel(bmp, x + 1, y + 4, 1)
        set_pixel(bmp, x, y + 5, 1)
    else:
        # Left arm down
        set_pixel(bmp, x + 1, y + 5, 1)
        set_pixel(bmp, x, y + 6, 1)
    
    if arm_up_right:
        # Right arm up
        set_pixel(bmp, x + 6, y + 4, 1)
        set_pixel(bmp, x + 7, y + 5, 1)
    else:
        # Right arm down
        set_pixel(bmp, x + 6, y + 5, 1)
        set_pixel(bmp, x + 7, y + 6, 1)
    
    # Legs (animated)
    if leg_apart:
        # Legs apart
        set_pixel(bmp, x + 2, y + 9, 1)
        set_pixel(bmp, x + 2, y + 10, 1)
        set_pixel(bmp, x + 5, y + 9, 1)
        set_pixel(bmp, x + 5, y + 10, 1)
    else:
        # Legs together
        set_pixel(bmp, x + 3, y + 9, 1)
        set_pixel(bmp, x + 3, y + 10, 1)
        set_pixel(bmp, x + 4, y + 9, 1)
        set_pixel(bmp, x + 4, y + 10, 1)


def draw_confetti(bmp, x, y, color):
    """Draw a small confetti piece."""
    set_pixel(bmp, x, y, color)


def init_animation():
    """Initialize gingerbread dance state."""
    # Create dancers
    dancers = [
        {"x": 10, "y": 10, "phase": 0},
        {"x": 26, "y": 10, "phase": math.pi / 2},
        {"x": 42, "y": 10, "phase": math.pi},
    ]
    
    # Create confetti
    confetti = []
    for i in range(30):
        confetti.append({
            "x": (i * 7 + 3) % WIDTH,
            "y": (i * 3 + 1) % HEIGHT,
            "color": [5, 6, 7, 8, 10][i % 5],
            "vy": 0.2 + (i % 3) * 0.1,
        })
    
    return {
        "dancers": dancers,
        "confetti": confetti,
        "frame": 0,
        "dance_speed": 0.15,
    }


def update_animation(state):
    """Update one frame of gingerbread dance animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Draw festive background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Create striped background
            if (x + y) % 8 < 4:
                bitmap[x, y] = 0   # dark red
            else:
                bitmap[x, y] = 11  # very dark red
    
    # Update and draw confetti
    for conf in state["confetti"]:
        conf["y"] += conf["vy"]
        if conf["y"] >= HEIGHT:
            conf["y"] = 0
            conf["x"] = (conf["x"] + 5) % WIDTH
        
        draw_confetti(bitmap, int(conf["x"]), int(conf["y"]), conf["color"])
    
    # Update dance animation
    dance_time = state["frame"] * state["dance_speed"]
    
    # Draw dancers with synchronized movements
    for i, dancer in enumerate(state["dancers"]):
        phase = dance_time + dancer["phase"]
        
        # Wave motion - up and down
        y_offset = int(2 * math.sin(phase))
        
        # Arm movements
        arm_up_left = math.sin(phase) > 0
        arm_up_right = math.sin(phase + math.pi) > 0
        
        # Leg movements
        leg_apart = math.sin(phase * 2) > 0
        
        # Draw the gingerbread person
        draw_gingerbread_person(
            bitmap,
            dancer["x"],
            dancer["y"] + y_offset,
            arm_up_left,
            arm_up_right,
            leg_apart
        )
        
        # Add sparkles around dancing gingerbread
        if state["frame"] % 5 == 0:
            sparkle_angle = phase * 2
            sx = int(dancer["x"] + 4 + 8 * math.cos(sparkle_angle))
            sy = int(dancer["y"] + 5 + 8 * math.sin(sparkle_angle))
            set_pixel(bitmap, sx, sy, 12)
    
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
