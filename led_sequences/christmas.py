"""
christmas.py - Smooth Christmas Story Animation for 64x32 LED matrix

Non-blocking animation with stable, flicker-free scenes:
1. Snowy Night - gentle snowfall with stars
2. Santa's Sleigh - flying across the sky
3. Cozy House - warm house with decorated tree
4. Gift Opening - presents appear with sparkles
5. Starry Finale - peaceful night sky

Each scene uses solid backgrounds with smooth sprite movement.
"""
print("Christmas Story loading")
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

    # Colorful palette
    palette[0] = (0, 0, 20)        # dark night blue
    palette[1] = (255, 255, 255)   # white snow/stars
    palette[2] = (220, 20, 60)     # red - santa/gifts
    palette[3] = (30, 140, 30)     # green tree
    palette[4] = (255, 215, 0)     # gold star/lights
    palette[5] = (100, 50, 20)     # brown house/trunk
    palette[6] = (255, 140, 0)     # orange window glow
    palette[7] = (65, 105, 225)    # blue sky accent
    palette[8] = (255, 192, 203)   # pink gift
    palette[9] = (138, 43, 226)    # purple gift
    palette[10] = (0, 191, 255)    # light blue gift
    palette[11] = (50, 205, 50)    # lime green
    palette[12] = (255, 69, 0)     # red-orange
    palette[13] = (255, 255, 150)  # pale yellow
    palette[14] = (180, 120, 80)   # tan/beige
    palette[15] = (10, 10, 40)     # deep night

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
    """Safely set pixel with bounds check."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        bmp[x, y] = c


def fill_rect(bmp, x, y, w, h, c):
    """Fill rectangle with bounds check."""
    for yy in range(y, min(y + h, HEIGHT)):
        for xx in range(x, min(x + w, WIDTH)):
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                bmp[xx, yy] = c


def init_animation():
    """Initialize Christmas story state."""
    # Precompute snowflakes with deterministic starting positions
    snowflakes = []
    for i in range(15):  # 15 gentle snowflakes
        x = (i * 4.3) % WIDTH
        y = (i * 2.1) % HEIGHT
        speed = 0.3 + (i % 3) * 0.15
        snowflakes.append([x, y, speed])
    
    # Precompute star positions
    stars = []
    for i in range(20):
        sx = (i * 7 + 3) % WIDTH
        sy = (i * 3 + 1) % 16  # top half only
        stars.append((sx, sy))
    
    return {
        "phase": "snowy_night",
        "phase_start": time.time(),
        "frame": 0,
        "snowflakes": snowflakes,
        "stars": stars,
        "santa_x": -15,         # Santa sleigh starts off-screen left
        "sparkle_frame": 0,
        "gift_delay": 0,
        "gifts_shown": 0,
        "text_alpha": 0,        # For text fade-in effect
    }


def draw_tree(bmp, x, y, with_ornaments=True):
    """Draw a classic pyramid-shaped Christmas tree."""
    # Trunk (brown)
    fill_rect(bmp, x - 1, y, 3, 2, 5)
    
    # Build pyramid from bottom to top (classic triangle shape)
    # Bottom layer - widest
    for dy in range(0, 3):
        width = 9 - dy * 2
        for dx in range(-width//2, width//2 + 1):
            set_pixel(bmp, x + dx, y - 2 - dy, 3)
    
    # Middle layer
    for dy in range(0, 3):
        width = 7 - dy * 2
        for dx in range(-width//2, width//2 + 1):
            set_pixel(bmp, x + dx, y - 5 - dy, 3)
    
    # Top layer
    for dy in range(0, 3):
        width = 5 - dy * 2
        for dx in range(-width//2, width//2 + 1):
            set_pixel(bmp, x + dx, y - 8 - dy, 3)
    
    # Top point
    set_pixel(bmp, x, y - 11, 3)
    set_pixel(bmp, x - 1, y - 10, 3)
    set_pixel(bmp, x + 1, y - 10, 3)
    
    # Golden star on top
    set_pixel(bmp, x, y - 12, 4)
    set_pixel(bmp, x - 1, y - 11, 4)
    set_pixel(bmp, x + 1, y - 11, 4)
    set_pixel(bmp, x, y - 10, 4)
    
    if with_ornaments:
        # Colorful ornaments (red, pink, purple, gold)
        set_pixel(bmp, x - 3, y - 3, 2)
        set_pixel(bmp, x + 3, y - 3, 8)
        set_pixel(bmp, x - 2, y - 5, 9)
        set_pixel(bmp, x + 2, y - 6, 4)
        set_pixel(bmp, x - 1, y - 7, 2)
        set_pixel(bmp, x + 1, y - 8, 10)
        set_pixel(bmp, x, y - 4, 4)
        set_pixel(bmp, x - 3, y - 6, 10)


def draw_santa_sleigh(bmp, x, y):
    """Draw Santa's sleigh with simple shapes."""
    # Sleigh body (red)
    fill_rect(bmp, x, y, 8, 3, 2)
    # Santa (red with white beard)
    set_pixel(bmp, x + 2, y - 1, 2)
    set_pixel(bmp, x + 3, y - 1, 1)  # beard
    set_pixel(bmp, x + 2, y - 2, 2)  # hat
    # Reindeer (brown front)
    set_pixel(bmp, x - 2, y, 5)
    set_pixel(bmp, x - 3, y, 5)
    set_pixel(bmp, x - 2, y - 1, 5)


def draw_house(bmp, x, y):
    """Draw a cozy house with warm glow."""
    # Walls (brown)
    fill_rect(bmp, x, y - 10, 12, 10, 5)
    # Roof (darker brown)
    fill_rect(bmp, x - 2, y - 13, 16, 3, 14)
    # Windows (warm yellow glow)
    fill_rect(bmp, x + 2, y - 7, 3, 3, 6)
    fill_rect(bmp, x + 7, y - 7, 3, 3, 6)
    # Door
    fill_rect(bmp, x + 5, y - 4, 2, 4, 12)


def draw_gift(bmp, x, y, color):
    """Draw a wrapped gift."""
    # Box
    fill_rect(bmp, x, y, 3, 3, color)
    # Ribbon (white)
    set_pixel(bmp, x + 1, y, 1)
    set_pixel(bmp, x + 1, y + 1, 1)
    set_pixel(bmp, x + 1, y + 2, 1)
    # Bow
    set_pixel(bmp, x + 1, y - 1, 1)


def draw_text_small(bmp, text, x, y, color):
    """Draw simple 3x5 pixel font text."""
    # Simple letter patterns (3 pixels wide, 5 tall)
    letters = {
        'M': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,0,1]],
        'E': [[1,1,1],[1,0,0],[1,1,1],[1,0,0],[1,1,1]],
        'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
        'Y': [[1,0,1],[1,0,1],[0,1,0],[0,1,0],[0,1,0]],
        'C': [[1,1,1],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
        'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
        'I': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
        'S': [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
        'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
        'A': [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
        ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
    }
    
    cursor_x = x
    for char in text.upper():
        if char in letters:
            pattern = letters[char]
            for row in range(5):
                for col in range(3):
                    if pattern[row][col]:
                        set_pixel(bmp, cursor_x + col, y + row, color)
            cursor_x += 4  # 3 pixel width + 1 pixel spacing


def update_animation(state):
    """Update one frame - smooth story progression."""
    state["frame"] += 1
    now = time.time()
    elapsed = now - state["phase_start"]
    phase = state["phase"]

    # Update snowflakes (gentle, always falling)
    for flake in state["snowflakes"]:
        flake[1] += flake[2]
        if flake[1] >= HEIGHT:
            flake[1] = 0

    # Phase transitions with smooth timing (extended scenes)
    if phase == "snowy_night" and elapsed > 10:
        state["phase"] = "santa_flying"
        state["phase_start"] = now
        state["santa_x"] = -15
    elif phase == "santa_flying":
        state["santa_x"] += 0.8  # smooth movement
        if state["santa_x"] > WIDTH + 5:
            state["phase"] = "cozy_house"
            state["phase_start"] = now
    elif phase == "cozy_house" and elapsed > 10:
        state["phase"] = "gifts_appear"
        state["phase_start"] = now
        state["gifts_shown"] = 0
        state["gift_delay"] = 0
    elif phase == "gifts_appear":
        # Gifts appear one by one
        state["gift_delay"] += 1
        if state["gift_delay"] > 30 and state["gifts_shown"] < 3:
            state["gifts_shown"] += 1
            state["gift_delay"] = 0
        if elapsed > 12:
            state["phase"] = "starry_finale"
            state["phase_start"] = now
    elif phase == "starry_finale" and elapsed > 10:
        state["phase"] = "merry_christmas"
        state["phase_start"] = now
        state["text_alpha"] = 0
    elif phase == "merry_christmas" and elapsed > 12:
        # Loop back to start
        state["phase"] = "snowy_night"
        state["phase_start"] = now

    # Update sparkle animation
    state["sparkle_frame"] = (state["sparkle_frame"] + 1) % 30

    # === DRAWING ===
    if not display_ok:
        return state

    # Clear with dark night background
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bitmap[x, y] = 0

    # === SCENE 1: Snowy Night ===
    if phase == "snowy_night":
        # Draw twinkling stars
        for i, (sx, sy) in enumerate(state["stars"]):
            if (state["frame"] + i * 3) % 20 < 10:
                set_pixel(bitmap, sx, sy, 1)
        
        # Draw gentle snowfall
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # Ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # === SCENE 2: Santa Flying ===
    elif phase == "santa_flying":
        # Stars in background
        for i, (sx, sy) in enumerate(state["stars"]):
            if i % 3 == 0:
                set_pixel(bitmap, sx, sy, 1)
        
        # Gentle snowfall continues
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # Santa's sleigh
        draw_santa_sleigh(bitmap, int(state["santa_x"]), HEIGHT // 2)
        
        # Trail sparkles behind santa
        for i in range(5):
            tx = int(state["santa_x"]) - i * 3
            ty = HEIGHT // 2 - 1 + (i % 2)
            if (state["frame"] + i) % 6 < 3:
                set_pixel(bitmap, tx, ty, 4)
        
        # Snowy ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # === SCENE 3: Cozy House ===
    elif phase == "cozy_house":
        # Night sky with stars
        for i, (sx, sy) in enumerate(state["stars"]):
            if (state["frame"] + i * 2) % 15 < 8:
                set_pixel(bitmap, sx, sy, 1)
        
        # Draw house
        draw_house(bitmap, 8, HEIGHT - 3)
        
        # Draw Christmas tree visible through window area
        draw_tree(bitmap, WIDTH - 12, HEIGHT - 3)
        
        # Gentle snow
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # Snowy ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # === SCENE 4: Gifts Appear ===
    elif phase == "gifts_appear":
        # Night sky
        for sx, sy in state["stars"]:
            set_pixel(bitmap, sx, sy, 1)
        
        # Gentle snowfall continues
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # House and tree
        draw_house(bitmap, 8, HEIGHT - 3)
        draw_tree(bitmap, WIDTH - 12, HEIGHT - 3)
        
        # Gifts appearing one by one with sparkles
        gift_colors = [2, 8, 9]  # red, pink, purple
        gift_x_positions = [WIDTH - 20, WIDTH - 16, WIDTH - 12]
        
        for i in range(state["gifts_shown"]):
            gx = gift_x_positions[i]
            gy = HEIGHT - 6
            draw_gift(bitmap, gx, gy, gift_colors[i])
            
            # Sparkles around newest gift
            if i == state["gifts_shown"] - 1 and state["gift_delay"] < 20:
                for dx in [-2, 2]:
                    for dy in [-2, 2]:
                        if state["sparkle_frame"] % 8 < 4:
                            set_pixel(bitmap, gx + 1 + dx, gy + 1 + dy, 4)
        
        # Ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # === SCENE 5: Starry Finale ===
    elif phase == "starry_finale":
        # Full starry sky
        for sx, sy in state["stars"]:
            set_pixel(bitmap, sx, sy, 1)
        
        # Extra twinkling stars
        for i in range(10):
            tx = (i * 11 + 5) % WIDTH
            ty = (i * 7 + 10) % 20
            if (state["frame"] + i) % 12 < 6:
                set_pixel(bitmap, tx, ty, 4)
        
        # Gentle snowfall continues
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # Peaceful tree silhouette
        draw_tree(bitmap, WIDTH // 2, HEIGHT - 3)
        
        # Gifts under tree
        draw_gift(bitmap, WIDTH // 2 - 8, HEIGHT - 6, 2)
        draw_gift(bitmap, WIDTH // 2 - 4, HEIGHT - 6, 8)
        draw_gift(bitmap, WIDTH // 2 + 4, HEIGHT - 6, 9)
        
        # Snowy ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # === SCENE 6: Merry Christmas Text ===
    elif phase == "merry_christmas":
        # Twinkling starry background
        for i, (sx, sy) in enumerate(state["stars"]):
            if (state["frame"] + i * 2) % 18 < 9:
                set_pixel(bitmap, sx, sy, 1)
        
        # Extra sparkles
        for i in range(15):
            tx = (i * 9 + 7) % WIDTH
            ty = (i * 5 + 3) % HEIGHT
            if (state["frame"] + i * 3) % 15 < 8:
                set_pixel(bitmap, tx, ty, 4)
        
        # Gentle snow
        for flake in state["snowflakes"]:
            x, y = int(flake[0]), int(flake[1])
            set_pixel(bitmap, x, y, 1)
        
        # Fade in text effect
        if elapsed < 2:
            # Gradual appearance
            if state["frame"] % 3 == 0:
                state["text_alpha"] = min(1, state["text_alpha"] + 0.05)
        
        # Draw "MERRY" on top line (centered)
        if state["text_alpha"] > 0.3:
            draw_text_small(bitmap, "MERRY", 14, 9, 2)
        
        # Draw "CHRISTMAS" on bottom line (one word)
        if state["text_alpha"] > 0.6:
            draw_text_small(bitmap, "CHRISTMAS", 2, 17, 3)
        
        # Decorative elements
        if elapsed > 1:
            # Little trees on far sides
            for tx in [4, WIDTH - 8]:
                # Mini tree
                set_pixel(bitmap, tx, HEIGHT - 4, 5)
                set_pixel(bitmap, tx - 1, HEIGHT - 5, 3)
                set_pixel(bitmap, tx, HEIGHT - 5, 3)
                set_pixel(bitmap, tx + 1, HEIGHT - 5, 3)
                set_pixel(bitmap, tx, HEIGHT - 6, 3)
                set_pixel(bitmap, tx, HEIGHT - 7, 4)
            
            # Santa's face on the right side (EXTRA LARGE with maximum detail)
            sx = WIDTH - 17
            sy = 5
            
            # Red hat (large and detailed)
            fill_rect(bitmap, sx + 1, sy, 8, 4, 2)         # Hat body red
            fill_rect(bitmap, sx + 2, sy - 1, 6, 1, 2)     # Hat top red
            set_pixel(bitmap, sx + 3, sy - 2, 2)           # Hat tip
            # Hat trim (fluffy white fur)
            fill_rect(bitmap, sx, sy + 4, 10, 2, 1)        # Hat trim white thick
            # Large pom-pom with shading
            fill_rect(bitmap, sx + 8, sy + 1, 3, 3, 1)     # White pom-pom
            set_pixel(bitmap, sx + 9, sy + 2, 13)          # Pom-pom highlight
            
            # Face outline and main color (beige/tan - extra large)
            fill_rect(bitmap, sx + 1, sy + 6, 8, 7, 14)    # Face main
            
            # Eyes (large with detail)
            # Left eye
            fill_rect(bitmap, sx + 2, sy + 7, 2, 3, 0)     # Left eye black
            set_pixel(bitmap, sx + 3, sy + 7, 7)           # Left eye sparkle top
            set_pixel(bitmap, sx + 2, sy + 8, 1)           # Left eye sparkle mid
            # Right eye  
            fill_rect(bitmap, sx + 6, sy + 7, 2, 3, 0)     # Right eye black
            set_pixel(bitmap, sx + 7, sy + 7, 7)           # Right eye sparkle top
            set_pixel(bitmap, sx + 6, sy + 8, 1)           # Right eye sparkle mid
            
            # Eyebrows (gray/dark)
            fill_rect(bitmap, sx + 2, sy + 6, 2, 1, 15)    # Left eyebrow
            fill_rect(bitmap, sx + 6, sy + 6, 2, 1, 15)    # Right eyebrow
            
            # Rosy cheeks (pink)
            fill_rect(bitmap, sx + 1, sy + 9, 2, 2, 8)     # Left cheek
            fill_rect(bitmap, sx + 7, sy + 9, 2, 2, 8)     # Right cheek
            
            # Nose (red, round and prominent)
            fill_rect(bitmap, sx + 4, sy + 9, 2, 2, 2)     # Nose main
            set_pixel(bitmap, sx + 5, sy + 9, 12)          # Nose highlight
            
            # Mouth (big smile)
            fill_rect(bitmap, sx + 3, sy + 11, 4, 1, 2)    # Smile
            set_pixel(bitmap, sx + 2, sy + 12, 2)          # Smile left curve
            set_pixel(bitmap, sx + 7, sy + 12, 2)          # Smile right curve
            
            # White mustache (big and bushy)
            fill_rect(bitmap, sx, sy + 10, 4, 2, 1)        # Left mustache
            fill_rect(bitmap, sx + 6, sy + 10, 4, 2, 1)    # Right mustache
            set_pixel(bitmap, sx + 1, sy + 12, 1)          # Mustache curl left
            set_pixel(bitmap, sx + 8, sy + 12, 1)          # Mustache curl right
            
            # White beard (full, fluffy and long)
            fill_rect(bitmap, sx, sy + 13, 10, 5, 1)       # Beard main body
            fill_rect(bitmap, sx + 1, sy + 18, 8, 2, 1)    # Beard mid layer
            fill_rect(bitmap, sx + 2, sy + 20, 6, 1, 1)    # Beard lower layer
            fill_rect(bitmap, sx + 3, sy + 21, 4, 1, 1)    # Beard point
            # Beard texture and shading
            set_pixel(bitmap, sx + 2, sy + 15, 13)         # Beard highlight left
            set_pixel(bitmap, sx + 7, sy + 15, 13)         # Beard highlight right
            set_pixel(bitmap, sx + 4, sy + 16, 13)         # Beard highlight center
            set_pixel(bitmap, sx + 1, sy + 14, 7)          # Beard shadow left
            set_pixel(bitmap, sx + 8, sy + 14, 7)          # Beard shadow right
        
        # Ground
        fill_rect(bitmap, 0, HEIGHT - 3, WIDTH, 3, 1)

    # Manual refresh to control timing and reduce flicker
    try:
        display.refresh()
    except:
        pass

    return state