import microcontroller
import supervisor

print("Code.py starting")

# List of available animations
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

# Get current animation index from NVM
current_index = microcontroller.nvm[0]
if current_index >= len(ANIMATIONS):
    current_index = 0

# Load and run the selected animation
anim_name = ANIMATIONS[current_index]
print(f"Loading animation: {anim_name}")
try:
    __import__(f"led_sequences.{anim_name}")
except Exception as e:
    print(f"Failed to load {anim_name}: {e}")
    # Fallback to first animation
    try:
        __import__("led_sequences.bouncing_balls")
    except Exception as e2:
        print(f"Fallback failed: {e2}")
        # Infinite loop to prevent crash
        while True:
            pass
