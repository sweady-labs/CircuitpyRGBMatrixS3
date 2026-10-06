"""
wreath_glow.py - Animated Christmas wreath with pulsing lights for 64x32 LED matrix

Non-blocking animation featuring a Christmas wreath with pulsing colorful
lights and a flowing ribbon.
"""
print("Wreath Glow loading")
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

    # Wreath color palette
    palette[0] = (0, 0, 0)         # black background
    palette[1] = (34, 139, 34)     # forest green (wreath)
    palette[2] = (50, 205, 50)     # lime green (highlight)
    palette[3] = (25, 100, 25)     # dark green (shadow)
    palette[4] = (220, 20, 60)     # red light
    palette[5] = (255, 215, 0)     # gold light
    palette[6] = (65, 105, 225)    # blue light
    palette[7] = (255, 255, 255)   # white light
    palette[8] = (255, 140, 0)     # orange light
    palette[9] = (138, 43, 226)    # purple light
    palette[10] = (200, 0, 0)      # red ribbon
    palette[11] = (255, 50, 50)    # bright red ribbon
    palette[12] = (150, 0, 0)      # dark red ribbon
    palette[13] = (100, 60, 20)    # brown branch
    palette[14] = (255, 255, 150)  # pale glow
    palette[15] = (180, 120, 30)   # gold accent

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


def draw_circle_outline(bmp, cx, cy, radius, color, thickness=1):
    """Draw a circle outline."""
    for angle_deg in range(0, 360, 3):
        angle = math.radians(angle_deg)
        for t in range(thickness):
            x = int(cx + (radius + t) * math.cos(angle))
            y = int(cy + (radius + t) * math.sin(angle))
            set_pixel(bmp, x, y, color)


def init_animation():
    """Initialize wreath glow state."""
    # Define light positions around the wreath
    lights = []
    light_colors = [4, 5, 6, 7, 8, 9]  # red, gold, blue, white, orange, purple
    
    for i in range(12):
        angle = (i / 12.0) * 2 * math.pi
        lights.append({
            "angle": angle,
            "color": light_colors[i % len(light_colors)],
            "phase": i * 0.5,
        })
    
    return {
        "lights": lights,
        "frame": 0,
        "pulse": 0.0,
        "ribbon_wave": 0.0,
    }


def update_animation(state):
    """Update one frame of wreath glow animation."""
    if not display_ok:
        time.sleep(0.05)
        return state
    
    # Clear background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0
    
    cx, cy = WIDTH // 2, HEIGHT // 2
    
    # Draw wreath base (multiple circles for thickness)
    draw_circle_outline(bitmap, cx, cy, 12, 3, 2)  # dark green inner
    draw_circle_outline(bitmap, cx, cy, 13, 1, 2)  # forest green
    draw_circle_outline(bitmap, cx, cy, 14, 2, 1)  # lime highlight
    draw_circle_outline(bitmap, cx, cy, 15, 1, 2)  # forest green outer
    
    # Add texture to wreath
    for angle_deg in range(0, 360, 15):
        angle = math.radians(angle_deg + state["frame"] * 0.5)
        x = int(cx + 13 * math.cos(angle))
        y = int(cy + 13 * math.sin(angle))
        set_pixel(bitmap, x, y, 2)  # lime highlights
    
    # Draw pulsing lights
    state["pulse"] += 0.15
    
    for light in state["lights"]:
        # Calculate light position
        radius = 13
        x = int(cx + radius * math.cos(light["angle"]))
        y = int(cy + radius * math.sin(light["angle"]))
        
        # Pulsing brightness
        brightness = (math.sin(state["pulse"] + light["phase"]) + 1) / 2
        
        if brightness > 0.5:
            # Draw bright light
            set_pixel(bitmap, x, y, light["color"])
            # Add glow
            if brightness > 0.7:
                set_pixel(bitmap, x + 1, y, 14)
                set_pixel(bitmap, x - 1, y, 14)
                set_pixel(bitmap, x, y + 1, 14)
                set_pixel(bitmap, x, y - 1, 14)
    
    # Draw flowing ribbon at bottom
    state["ribbon_wave"] += 0.2
    ribbon_y = cy + 8
    
    for x in range(cx - 8, cx + 9):
        wave_offset = int(2 * math.sin((x - cx) * 0.3 + state["ribbon_wave"]))
        y = ribbon_y + wave_offset
        
        # Ribbon with shading
        set_pixel(bitmap, x, y, 10)      # red
        set_pixel(bitmap, x, y + 1, 11)  # bright red
        set_pixel(bitmap, x, y + 2, 12)  # dark red
        
        # Ribbon tails
        if x == cx - 8 or x == cx + 8:
            for dy in range(3, 7):
                set_pixel(bitmap, x, y + dy, 10)
    
    # Draw bow at ribbon center
    bow_x, bow_y = cx, ribbon_y - 2
    # Left loop
    set_pixel(bitmap, bow_x - 2, bow_y, 11)
    set_pixel(bitmap, bow_x - 3, bow_y - 1, 11)
    set_pixel(bitmap, bow_x - 2, bow_y - 2, 11)
    # Right loop
    set_pixel(bitmap, bow_x + 2, bow_y, 11)
    set_pixel(bitmap, bow_x + 3, bow_y - 1, 11)
    set_pixel(bitmap, bow_x + 2, bow_y - 2, 11)
    # Center knot
    set_pixel(bitmap, bow_x, bow_y, 12)
    set_pixel(bitmap, bow_x, bow_y - 1, 11)
    
    state["frame"] += 1
    
    try:
        display.refresh(minimum_frames_per_second=0)
    except:
        pass
    
    return state
