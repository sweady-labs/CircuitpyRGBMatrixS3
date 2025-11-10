import time
import board
import displayio
import digitalio
import framebufferio
import rgbmatrix

# Compatibility shim: older CircuitPython examples used display.show(group).
# In newer releases .show() was removed in favor of assigning display.root_group.
# Add a tiny shim to avoid AttributeError if some code (or a copy/paste) still
# calls display.show(...).
if not hasattr(framebufferio.FramebufferDisplay, "show"):
    def _compat_show(self, root_group):
        self.root_group = root_group
    framebufferio.FramebufferDisplay.show = _compat_show

displayio.release_displays()

# Adjust to your panel resolution
WIDTH = 64
HEIGHT = 32

# Hardware diagnostic: briefly pulse the output-enable (OE) pin before the
# rgbmatrix driver attaches to it. Many HUB75 panels use OE active-low, so
# pulling it low should enable outputs. We deinit the DigitalInOut afterwards
# so the rgbmatrix driver can then take control. Placing this before creating
# the RGBMatrix increases the chance the probe can drive the pin successfully.
try:
    oe = digitalio.DigitalInOut(board.MTX_OE)
    oe.direction = digitalio.Direction.OUTPUT
    for i in range(2):
        print("OE test: drive LOW (outputs enabled)")
        oe.value = False
        time.sleep(0.25)
        print("OE test: drive HIGH (outputs disabled)")
        oe.value = True
        time.sleep(0.25)
    oe.deinit()
except Exception as e:
    # If it's already in use by the driver, that's fine — we just continue.
    print("OE diagnostic failed:", e)

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=4,
    rgb_pins=[
        board.MTX_R1, board.MTX_G1, board.MTX_B1,
        board.MTX_R2, board.MTX_G2, board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
        # if your panel has no E line, comment this out:
        # board.MTX_ADDRE,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

bitmap = displayio.Bitmap(WIDTH, HEIGHT, 8)
palette = displayio.Palette(8)

palette[0] = 0x000000  # black
palette[1] = 0xFF0000  # red
palette[2] = 0x00FF00  # green
palette[3] = 0x0000FF  # blue
palette[4] = 0xFFFF00  # yellow 
palette[5] = 0xFF00FF  # magenta
palette[6] = 0x00FFFF  # cyan
palette[7] = 0xFFFFFF  # white

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
group = displayio.Group()
group.append(tg)

# Draw an initial test pattern so the panel shows something immediately.
for yy in range(HEIGHT):
    for xx in range(WIDTH):
        # checker-ish pattern using palette index 7 (white) and 1 (red)
        bitmap[xx, yy] = 7 if ((xx + yy) % 6) < 3 else 1


# OLD (removed): display.show(group)
display.root_group = group  # ✅ new way

print("Display root_group assigned; starting main loop")

# Show a full-white test for a few seconds so you can visually confirm the
# panel is receiving data/power. If you see nothing here, check 5V/GND and OE.
for yy in range(HEIGHT):
    for xx in range(WIDTH):
        bitmap[xx, yy] = 7
print("Showing full-white test for 5 seconds")
time.sleep(5)

# Restore checker-ish pattern to start animation
for yy in range(HEIGHT):
    for xx in range(WIDTH):
        bitmap[xx, yy] = 7 if ((xx + yy) % 6) < 3 else 1

x = 0
color_index = 1

while True:
    # clear
    for y in range(HEIGHT):
        for xx in range(WIDTH):
            bitmap[xx, y] = 0

    # moving vertical bar
    for y in range(HEIGHT):
        bitmap[x % WIDTH, y] = color_index

    x += 1
    if x % WIDTH == 0:
        color_index = 1 + (color_index % 7)

    # occasional heartbeat on serial so we can see the loop is running
    if x % (WIDTH * 10) == 0:
        print("loop x=", x, "color=", color_index)

    time.sleep(0.03)
