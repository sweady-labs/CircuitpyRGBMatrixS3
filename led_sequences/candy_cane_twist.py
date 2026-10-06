"""
candy_cane_twist.py - Rotating candy cane spiral animation for 64x32 LED matrix

Non-blocking animation featuring rotating red and white spiral stripes
that create a mesmerizing candy cane effect.
"""
print("Candy Cane Twist loading")
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
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
    palette = displayio.Palette(8)

    # Candy cane color palette
    palette[0] = (0, 0, 0)         # black background
    palette[1] = (255, 255, 255)   # white stripe
    palette[2] = (220, 20, 60)     # red stripe
    palette[3] = (255, 105, 180)   # pink highlight
    palette[4] = (200, 200, 200)   # light gray
    palette[5] = (180, 0, 40)      # dark red
    palette[6] = (255, 215, 0)     # gold accent
    palette[7] = (150, 10, 30)     # deep red

    tg = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tg)
    display.root_group = group
    display_ok = True
    print("Display ready")
except Exception as e:
    print("Display failed:", e)
    display_ok = False


def init_animation():
    """Initialize candy cane twist state."""
    return {
        "angle": 0.0,
        "frame": 0,
        "stripe_width": 8,
        "speed": 0.08,
    }


def update_animation(state):
    """Update one frame of candy cane twist animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Clear background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    # Update rotation angle
    state["angle"] += state["speed"]
    if state["angle"] > 2 * math.pi:
        state["angle"] -= 2 * math.pi
    
    # Draw rotating spiral stripes
    cx = WIDTH / 2
    cy = HEIGHT / 2
    
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Calculate position relative to center
            dx = x - cx
            dy = y - cy
            
            # Calculate distance and angle
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            
            # Create spiral effect
            spiral_value = (angle + state["angle"] + dist * 0.15) % (2 * math.pi)
            stripe_pos = int((spiral_value / (2 * math.pi)) * state["stripe_width"])
            
            # Determine color based on stripe position
            if stripe_pos % 2 == 0:
                # White stripe with highlights
                if dist > 2 and dist < 18:
                    color = 1  # white
                elif dist >= 18:
                    color = 4  # light gray
                else:
                    color = 0
            else:
                # Red stripe with variations
                if dist > 2 and dist < 18:
                    if (x + y) % 3 == 0:
                        color = 2  # bright red
                    else:
                        color = 5  # dark red
                elif dist >= 18:
                    color = 7  # deep red
                else:
                    color = 0
            
            bitmap[x, y] = color
    
    # Add sparkle accents at certain positions
    sparkle_positions = [
        (int(cx + 10 * math.cos(state["angle"])), int(cy + 10 * math.sin(state["angle"]))),
        (int(cx + 10 * math.cos(state["angle"] + math.pi)), int(cy + 10 * math.sin(state["angle"] + math.pi))),
        (int(cx + 15 * math.cos(state["angle"] + math.pi/2)), int(cy + 15 * math.sin(state["angle"] + math.pi/2))),
        (int(cx + 15 * math.cos(state["angle"] - math.pi/2)), int(cy + 15 * math.sin(state["angle"] - math.pi/2))),
    ]
    
    for sx, sy in sparkle_positions:
        if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
            if state["frame"] % 10 < 5:
                bitmap[sx, sy] = 6  # gold sparkle
    
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
