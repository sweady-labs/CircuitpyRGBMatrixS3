"""Boot script - Initialize NVM and optionally load animations"""
import microcontroller
import supervisor

ANIMATIONS = ["bouncing_balls", "breathing", "cap-shield", "dna", "fireworks", "game_of_life",
              "ironman", "kaleidoscope", "matrix_rain", "moving-lines", "plasma", "rain",
              "scrolling_text", "warp", "strange_things", "christmas", "tetris"]

# Initialize NVM if needed
# NVM[0] = animation index (0-16)
# NVM[1] = mode (0=load animation, 1=web server, 255=first boot)

try:
    mode = microcontroller.nvm[1]
    anim_idx = microcontroller.nvm[0]
except:
    mode = 255
    anim_idx = 0

# First boot
if mode == 255 or mode > 1:
    microcontroller.nvm[1] = 1  # Default to web mode
    microcontroller.nvm[0] = 0
    print("First boot - initialized NVM")

# If mode=0, we should load animation instead of web server
# This is controlled by code.py, not boot.py
