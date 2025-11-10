"""
button_test.py (temporary)
Simple, safe script that prints UP/DOWN button events and a heartbeat.
Use this to verify the serial monitor and buttons without running the full
animation set. It deliberately avoids display and heavy imports.

Replace the original `code.py` later with your animation switcher.
"""

import time
import board
import keypad

print("Animation switcher with safe fallback")

import microcontroller
import supervisor
import sys

# List all animation modules to cycle through (must match filenames in led_sequences)
ANIMATIONS = [
    "bouncing_balls",
    "breathing",
    "cap-shield",
    "dna",
    "fireworks",
    "game_of_life",
    "ironman",
    "kaleidoscope",
    "matrix_rain",
    "moving-lines",
    "plasma",
    "rain",
    "scrolling_text",
    "warp",
    "strange_things",
    "christmas",
    "tetris",
]

# Read current index from NVM (single byte)
current_index = microcontroller.nvm[0]
if current_index >= len(ANIMATIONS):
    current_index = 0
    microcontroller.nvm[0] = 0

# Buttons will be created later (after attempting to start the menu)

# Decide whether to show the on-screen menu or run the selected animation.
# If the user holds BOTH UP and DOWN buttons at boot, launch the menu so they
# can pick. Otherwise import the animation module stored in NVM and run it.
import digitalio

# helper to check button pressed state (buttons are active-low on many S3 boards)
def _is_pressed(pin):
    d = digitalio.DigitalInOut(pin)
    d.direction = digitalio.Direction.INPUT
    try:
        d.pull = digitalio.Pull.UP
    except Exception:
        # some builds may not support setting pull again; ignore
        pass
    val = not d.value
    d.deinit()
    return val

both_held = False
try:
    if _is_pressed(board.BUTTON_UP) and _is_pressed(board.BUTTON_DOWN):
        both_held = True
except Exception:
    # If digitalio isn't available or pins can't be read, fall back to menu
    both_held = True

# Support a software request to show the menu: animations can set
# microcontroller.nvm[1] = 1 and call supervisor.reload() to force the
# menu to appear on the next soft-reboot. Clear the flag after reading.
try:
    forced_menu = microcontroller.nvm[1] == 1
    if forced_menu:
        microcontroller.nvm[1] = 0
        both_held = True
except Exception:
    # ignore if NVM access fails for some reason
    pass

if both_held:
    # Start the on-screen menu so the user can choose an animation
    try:
        print("Starting menu... (hold BOTH UP+DOWN at boot to show menu)")
        import led_sequences.menu as menu
    except Exception as e:
        print("Failed to start menu:", e)
        try:
            print(repr(e))
        except Exception:
            print(str(e))
        # Fallback to serial interactive mode (same as before)
        print("Entering fallback interactive mode. Press UP/DOWN to change NVM entry.")
        # create buttons here (menu may have avoided creating them)
        try:
            buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)
        except Exception as be:
            print("Warning: could not initialize buttons:", be)
            buttons = None
        print("Available animations:")
        for i, name in enumerate(ANIMATIONS):
            marker = "*" if i == current_index else " "
            print(f" {marker} [{i}] {name}")
        last_heartbeat = 0.0
        hb_interval = 2.0
        while True:
            event = None
            if buttons:
                event = buttons.events.get()
            if event:
                print(f"EVENT pressed={event.pressed}, key={event.key_number}")
                if event.pressed:
                    if event.key_number == 0:
                        current_index = (current_index + 1) % len(ANIMATIONS)
                        microcontroller.nvm[0] = current_index
                        print(f"--> NEXT: {ANIMATIONS[current_index]}")
                    elif event.key_number == 1:
                        current_index = (current_index - 1) % len(ANIMATIONS)
                        microcontroller.nvm[0] = current_index
                        print(f"--> PREV: {ANIMATIONS[current_index]}")
                    print("Press RESET (or soft reboot Ctrl-D) to load the selected animation")

            now = time.monotonic()
            if now - last_heartbeat >= hb_interval:
                last_heartbeat = now
                print(f"heartbeat {now:.1f}")
            time.sleep(0.05)
else:
    # Not holding both buttons — run the selected animation from NVM.
    anim_name = ANIMATIONS[current_index]
    print(f"Loading animation [{current_index}]: {anim_name}")
    try:
        # Importing the module will run its code (animations typically have a
        # top-level loop). This keeps the behavior simple: selected animation
        # modules run immediately.
        __import__(f"led_sequences.{anim_name}")
    except Exception as e:
        print(f"Failed to load animation '{anim_name}':", e)
        try:
            print(repr(e))
        except Exception:
            print(str(e))
        print("Entering fallback interactive mode on serial. You can change the NVM index with UP/DOWN and then RESET to try another animation.")
        last_heartbeat = 0.0
        hb_interval = 2.0
        # create buttons here as above
        try:
            buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)
        except Exception as be:
            print("Warning: could not initialize buttons:", be)
            buttons = None
        while True:
            event = None
            if buttons:
                event = buttons.events.get()
            if event:
                print(f"EVENT pressed={event.pressed}, key={event.key_number}")
                if event.pressed:
                    if event.key_number == 0:
                        current_index = (current_index + 1) % len(ANIMATIONS)
                        microcontroller.nvm[0] = current_index
                        print(f"--> NEXT: {ANIMATIONS[current_index]}")
                    elif event.key_number == 1:
                        current_index = (current_index - 1) % len(ANIMATIONS)
                        microcontroller.nvm[0] = current_index
                        print(f"--> PREV: {ANIMATIONS[current_index]}")
                    print("Press RESET (or soft reboot Ctrl-D) to load the selected animation")

            now = time.monotonic()
            if now - last_heartbeat >= hb_interval:
                last_heartbeat = now
                print(f"heartbeat {now:.1f}")
            time.sleep(0.05)
