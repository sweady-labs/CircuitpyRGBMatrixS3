"""
ornament_bounce.py - Bouncing Christmas ornaments with sparkle trails for 64x32 LED matrix

Non-blocking animation featuring colorful ornament balls that bounce around
with physics simulation and leave sparkle trails.
"""
print("Ornament Bounce loading")
import time
import board
import displayio
import framebufferio
import rgbmatrix
import random

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

    # Festive ornament colors
    palette[0] = (0, 0, 0)         # black background
    palette[1] = (220, 20, 60)     # red ornament
    palette[2] = (30, 200, 30)     # green ornament
    palette[3] = (50, 50, 255)     # blue ornament
    palette[4] = (255, 215, 0)     # gold ornament
    palette[5] = (255, 105, 180)   # pink ornament
    palette[6] = (138, 43, 226)    # purple ornament
    palette[7] = (255, 140, 0)     # orange ornament
    palette[8] = (255, 255, 255)   # white sparkle
    palette[9] = (255, 255, 150)   # pale yellow sparkle
    palette[10] = (150, 30, 30)    # dark red
    palette[11] = (20, 120, 20)    # dark green
    palette[12] = (30, 30, 180)    # dark blue
    palette[13] = (180, 150, 0)    # dark gold
    palette[14] = (100, 100, 100)  # gray
    palette[15] = (200, 200, 200)  # light gray

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
    """Initialize ornament bounce state."""
    # Create ornaments with physics properties
    ornaments = []
    colors = [1, 2, 3, 4, 5, 6, 7]
    
    for i in range(8):
        ornaments.append({
            "x": 10 + i * 7,
            "y": 5 + (i % 3) * 5,
            "vx": (i % 3 - 1) * 0.8 + 0.3,
            "vy": (i % 2) * 0.5 + 0.2,
            "color": colors[i % len(colors)],
            "radius": 2,
        })
    
    return {
        "ornaments": ornaments,
        "sparkles": [],
        "frame": 0,
        "gravity": 0.15,
    }


def draw_circle(bmp, cx, cy, radius, color):
    """Draw a filled circle."""
    for y in range(max(0, cy - radius), min(HEIGHT, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(WIDTH, cx + radius + 1)):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= radius * radius:
                bmp[x, y] = color


def update_animation(state):
    """Update one frame of ornament bounce animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Clear background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    # Update and draw ornaments
    for orb in state["ornaments"]:
        # Apply gravity
        orb["vy"] += state["gravity"]
        
        # Update position
        orb["x"] += orb["vx"]
        orb["y"] += orb["vy"]
        
        # Bounce off walls
        if orb["x"] <= orb["radius"] or orb["x"] >= WIDTH - orb["radius"]:
            orb["vx"] = -orb["vx"] * 0.85  # damping
            orb["x"] = max(orb["radius"], min(WIDTH - orb["radius"], orb["x"]))
            # Add sparkle on collision
            state["sparkles"].append({"x": int(orb["x"]), "y": int(orb["y"]), "life": 10})
        
        # Bounce off floor/ceiling
        if orb["y"] <= orb["radius"] or orb["y"] >= HEIGHT - orb["radius"]:
            orb["vy"] = -orb["vy"] * 0.85  # damping
            orb["y"] = max(orb["radius"], min(HEIGHT - orb["radius"], orb["y"]))
            # Add sparkle on collision
            state["sparkles"].append({"x": int(orb["x"]), "y": int(orb["y"]), "life": 10})
        
        # Draw ornament with shading
        cx, cy = int(orb["x"]), int(orb["y"])
        draw_circle(bitmap, cx, cy, orb["radius"], orb["color"])
        
        # Add highlight
        if 0 <= cx - 1 < WIDTH and 0 <= cy - 1 < HEIGHT:
            bitmap[cx - 1, cy - 1] = 15
    
    # Update and draw sparkles
    new_sparkles = []
    for sparkle in state["sparkles"]:
        if sparkle["life"] > 0:
            x, y = sparkle["x"], sparkle["y"]
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                color = 8 if sparkle["life"] > 5 else 9
                bitmap[x, y] = color
                # Additional sparkle pixels
                if sparkle["life"] > 7:
                    if x + 1 < WIDTH:
                        bitmap[x + 1, y] = color
                    if x - 1 >= 0:
                        bitmap[x - 1, y] = color
            sparkle["life"] -= 1
            new_sparkles.append(sparkle)
    
    state["sparkles"] = new_sparkles
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
