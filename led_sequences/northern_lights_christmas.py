"""
northern_lights_christmas.py - Aurora borealis with snowfall for 64x32 LED matrix

Non-blocking animation featuring beautiful northern lights (aurora) effect
with gentle snowfall creating a magical Christmas atmosphere.
"""
print("Northern Lights Christmas loading")
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

    # Aurora and winter color palette
    palette[0] = (0, 0, 20)        # dark night sky
    palette[1] = (0, 255, 100)     # green aurora
    palette[2] = (0, 200, 255)     # cyan aurora
    palette[3] = (100, 0, 255)     # purple aurora
    palette[4] = (0, 150, 50)      # dark green aurora
    palette[5] = (50, 100, 200)    # blue aurora
    palette[6] = (150, 0, 200)     # magenta aurora
    palette[7] = (255, 255, 255)   # white snow
    palette[8] = (200, 200, 200)   # light gray snow
    palette[9] = (50, 255, 150)    # bright green aurora
    palette[10] = (20, 20, 80)     # medium night sky
    palette[11] = (10, 10, 50)     # lighter night sky
    palette[12] = (255, 255, 200)  # pale yellow stars
    palette[13] = (0, 100, 30)     # very dark green
    palette[14] = (30, 60, 150)    # medium blue
    palette[15] = (80, 0, 120)     # dark purple

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


def init_animation():
    """Initialize northern lights state."""
    # Create snowflakes
    snowflakes = []
    for i in range(20):
        snowflakes.append({
            "x": (i * 3.7) % WIDTH,
            "y": (i * 2.3) % HEIGHT,
            "speed": 0.2 + (i % 4) * 0.1,
            "drift": (i % 3 - 1) * 0.05,
        })
    
    # Create stars
    stars = []
    for i in range(15):
        stars.append({
            "x": (i * 5 + 7) % WIDTH,
            "y": (i * 2 + 3) % 8,  # top portion only
            "brightness": i % 3,
        })
    
    return {
        "snowflakes": snowflakes,
        "stars": stars,
        "frame": 0,
        "wave_offset": 0.0,
        "aurora_phase": 0.0,
    }


def update_animation(state):
    """Update one frame of northern lights animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Draw gradient sky background
    for y in range(HEIGHT):
        darkness = y / HEIGHT
        if darkness < 0.3:
            bg_color = 10  # medium night
        elif darkness < 0.6:
            bg_color = 11  # lighter night
        else:
            bg_color = 0   # dark night
        
        for x in range(WIDTH):
            bitmap[x, y] = bg_color
    
    # Draw twinkling stars
    for star in state["stars"]:
        twinkle = (state["frame"] + star["brightness"] * 10) % 30
        if twinkle < 20:
            set_pixel(bitmap, int(star["x"]), int(star["y"]), 12)
    
    # Draw aurora borealis with flowing waves
    state["aurora_phase"] += 0.1
    state["wave_offset"] += 0.05
    
    for x in range(WIDTH):
        # Create multiple wave layers for aurora effect
        wave1 = 8 + int(4 * math.sin(x * 0.2 + state["wave_offset"]))
        wave2 = 10 + int(3 * math.sin(x * 0.15 + state["wave_offset"] * 1.5))
        wave3 = 12 + int(4 * math.sin(x * 0.25 + state["wave_offset"] * 0.8))
        
        # Phase determines color cycling
        phase = (x + state["aurora_phase"]) % 60
        
        # Draw layered aurora
        for y in range(max(0, wave1 - 3), min(HEIGHT, wave1 + 3)):
            intensity = 1.0 - abs(y - wave1) / 3.0
            if intensity > 0.3:
                if phase < 20:
                    color = 1  # green
                elif phase < 40:
                    color = 2  # cyan
                else:
                    color = 3  # purple
                set_pixel(bitmap, x, y, color)
        
        for y in range(max(0, wave2 - 2), min(HEIGHT, wave2 + 2)):
            intensity = 1.0 - abs(y - wave2) / 2.0
            if intensity > 0.4:
                if phase < 20:
                    color = 9  # bright green
                elif phase < 40:
                    color = 5  # blue
                else:
                    color = 6  # magenta
                set_pixel(bitmap, x, y, color)
        
        for y in range(max(0, wave3 - 2), min(HEIGHT, wave3 + 2)):
            intensity = 1.0 - abs(y - wave3) / 2.0
            if intensity > 0.5:
                if phase < 20:
                    color = 4  # dark green
                elif phase < 40:
                    color = 14  # medium blue
                else:
                    color = 15  # dark purple
                set_pixel(bitmap, x, y, color)
    
    # Draw falling snow
    for flake in state["snowflakes"]:
        # Update position
        flake["y"] += flake["speed"]
        flake["x"] += flake["drift"]
        
        # Wrap around
        if flake["y"] >= HEIGHT:
            flake["y"] = 0
            flake["x"] = (flake["x"] + 10) % WIDTH
        if flake["x"] < 0:
            flake["x"] += WIDTH
        elif flake["x"] >= WIDTH:
            flake["x"] -= WIDTH
        
        # Draw snowflake
        fx, fy = int(flake["x"]), int(flake["y"])
        set_pixel(bitmap, fx, fy, 7)
        
        # Add sparkle
        if state["frame"] % 3 == 0:
            set_pixel(bitmap, fx, fy, 8)
    
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
