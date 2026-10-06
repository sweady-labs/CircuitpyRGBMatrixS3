"""
advent_calendar.py - Interactive advent calendar animation for 64x32 LED matrix

Non-blocking animation featuring 24 doors that light up sequentially,
with surprises revealed behind each door.
"""
print("Advent Calendar loading")
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
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 16)
    palette = displayio.Palette(16)

    # Advent calendar palette
    palette[0] = (0, 0, 30)        # dark blue background
    palette[1] = (139, 69, 19)     # brown door
    palette[2] = (205, 133, 63)    # tan door frame
    palette[3] = (255, 215, 0)     # gold number
    palette[4] = (220, 20, 60)     # red surprise (present)
    palette[5] = (34, 139, 34)     # green surprise (tree)
    palette[6] = (255, 255, 255)   # white surprise (star/snow)
    palette[7] = (255, 140, 0)     # orange surprise (candle)
    palette[8] = (138, 43, 226)    # purple surprise (ornament)
    palette[9] = (255, 105, 180)   # pink surprise (candy)
    palette[10] = (100, 50, 20)    # dark brown
    palette[11] = (255, 255, 150)  # pale yellow glow
    palette[12] = (200, 0, 0)      # bright red
    palette[13] = (50, 50, 150)    # medium blue
    palette[14] = (150, 150, 150)  # gray
    palette[15] = (255, 200, 50)   # golden glow

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


def draw_number(bmp, x, y, num, color):
    """Draw a simple number (1-24)."""
    # Simple digit drawing (just vertical and horizontal bars)
    digits = {
        1: [[1], [1], [1]],
        2: [[1,1], [0,1], [1,0]],
        3: [[1,1], [0,1], [1,1]],
        4: [[1,0], [1,1], [0,1]],
        5: [[1,1], [1,0], [1,1]],
        6: [[1,0], [1,1], [1,1]],
        7: [[1,1], [0,1], [0,1]],
        8: [[1,1], [1,1], [1,1]],
        9: [[1,1], [1,1], [0,1]],
        0: [[1,1], [1,1], [1,1]],
    }
    
    if num < 10:
        pattern = digits.get(num, [[1]])
        for dy, row in enumerate(pattern):
            for dx, pixel in enumerate(row):
                if pixel:
                    set_pixel(bmp, x + dx, y + dy, color)
    else:
        # Two digits
        tens = num // 10
        ones = num % 10
        pattern1 = digits.get(tens, [[1]])
        pattern2 = digits.get(ones, [[1]])
        for dy, row in enumerate(pattern1):
            for dx, pixel in enumerate(row):
                if pixel:
                    set_pixel(bmp, x + dx, y + dy, color)
        for dy, row in enumerate(pattern2):
            for dx, pixel in enumerate(row):
                if pixel:
                    set_pixel(bmp, x + dx + 3, y + dy, color)


def draw_surprise(bmp, x, y, surprise_type):
    """Draw surprise icon behind the door."""
    if surprise_type == "present":
        # Gift box
        fill_rect(bmp, x, y + 1, 4, 3, 4)
        set_pixel(bmp, x + 1, y, 3)
        set_pixel(bmp, x + 2, y, 3)
    elif surprise_type == "tree":
        # Small tree
        set_pixel(bmp, x + 2, y, 5)
        set_pixel(bmp, x + 1, y + 1, 5)
        set_pixel(bmp, x + 2, y + 1, 5)
        set_pixel(bmp, x + 3, y + 1, 5)
        set_pixel(bmp, x + 2, y + 2, 10)
        set_pixel(bmp, x + 2, y + 3, 10)
    elif surprise_type == "star":
        # Star
        set_pixel(bmp, x + 2, y, 6)
        set_pixel(bmp, x + 1, y + 1, 6)
        set_pixel(bmp, x + 2, y + 1, 6)
        set_pixel(bmp, x + 3, y + 1, 6)
        set_pixel(bmp, x + 2, y + 2, 6)
    elif surprise_type == "candle":
        # Candle
        set_pixel(bmp, x + 2, y, 3)
        fill_rect(bmp, x + 1, y + 1, 3, 3, 7)
    elif surprise_type == "ornament":
        # Ornament ball
        set_pixel(bmp, x + 2, y, 3)
        fill_rect(bmp, x + 1, y + 1, 3, 3, 8)
    elif surprise_type == "candy":
        # Candy cane
        fill_rect(bmp, x + 1, y, 2, 3, 9)
        set_pixel(bmp, x + 3, y + 1, 9)


def init_animation():
    """Initialize advent calendar state."""
    # Define 24 doors with positions and surprises
    doors = []
    surprises = ["present", "tree", "star", "candle", "ornament", "candy"]
    
    for i in range(24):
        row = i // 6
        col = i % 6
        doors.append({
            "num": i + 1,
            "x": col * 10 + 2,
            "y": row * 7 + 2,
            "open": False,
            "opening_frame": 0,
            "surprise": surprises[i % len(surprises)],
        })
    
    return {
        "doors": doors,
        "frame": 0,
        "current_opening": 0,
        "open_delay": 60,  # Frames between each door opening
    }


def update_animation(state):
    """Update one frame of advent calendar animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Clear background with festive color
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    # Automatically open doors one by one
    if state["current_opening"] < 24 and state["frame"] % state["open_delay"] == 0:
        state["doors"][state["current_opening"]]["open"] = True
        state["current_opening"] += 1
    
    # Draw all doors
    for door in state["doors"]:
        x, y = door["x"], door["y"]
        
        if door["open"]:
            # Door is open - show surprise
            door["opening_frame"] += 1
            
            # Draw surprise
            draw_surprise(bitmap, x + 2, y + 1, door["surprise"])
            
            # Add sparkle effect when opening
            if door["opening_frame"] < 30:
                if door["opening_frame"] % 5 < 3:
                    set_pixel(bitmap, x, y, 11)
                    set_pixel(bitmap, x + 7, y, 11)
                    set_pixel(bitmap, x, y + 5, 11)
                    set_pixel(bitmap, x + 7, y + 5, 11)
            
            # Draw open door frame
            # Top and bottom
            for dx in range(8):
                set_pixel(bitmap, x + dx, y, 2)
                set_pixel(bitmap, x + dx, y + 5, 2)
            # Sides
            for dy in range(6):
                set_pixel(bitmap, x, y + dy, 2)
                set_pixel(bitmap, x + 7, y + dy, 2)
        else:
            # Door is closed
            # Draw door
            fill_rect(bitmap, x, y, 8, 6, 1)
            # Frame
            for dx in range(8):
                set_pixel(bitmap, x + dx, y, 2)
                set_pixel(bitmap, x + dx, y + 5, 2)
            for dy in range(6):
                set_pixel(bitmap, x, y + dy, 2)
                set_pixel(bitmap, x + 7, y + dy, 2)
            
            # Draw number
            draw_number(bitmap, x + 2, y + 1, door["num"], 3)
            
            # Pulsing effect on next door to open
            if state["doors"].index(door) == state["current_opening"]:
                if state["frame"] % 20 < 10:
                    # Highlight frame
                    for dx in range(8):
                        set_pixel(bitmap, x + dx, y, 15)
                        set_pixel(bitmap, x + dx, y + 5, 15)
                    for dy in range(6):
                        set_pixel(bitmap, x, y + dy, 15)
                        set_pixel(bitmap, x + 7, y + dy, 15)
    
    state["frame"] += 1
    
    # Reset after all doors are open and displayed for a while
    if state["current_opening"] >= 24 and state["frame"] > 24 * state["open_delay"] + 200:
        state["current_opening"] = 0
        state["frame"] = 0
        for door in state["doors"]:
            door["open"] = False
            door["opening_frame"] = 0
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
