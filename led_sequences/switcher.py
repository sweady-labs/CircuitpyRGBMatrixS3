import microcontroller
import supervisor
import board

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

# Get current index
current_index = microcontroller.nvm[0]
if current_index >= len(ANIMATIONS):
    current_index = 0

# Lazy-load buttons (only when needed)
buttons = None
buttons_initialized = False

def _init_buttons():
    """Initialize buttons on first use"""
    global buttons, buttons_initialized
    if buttons_initialized:
        return
    buttons_initialized = True
    try:
        import keypad
        buttons = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)
    except Exception as e:
        print(f"Button init failed: {e}")
        buttons = None

def check_switch():
    """Check for button presses and switch animation if needed."""
    _init_buttons()
    if not buttons:
        return False
    try:
        event = buttons.events.get()
        if event and event.pressed:
            print(f"Button {event.key_number} pressed")
            if event.key_number == 0:  # UP
                new_index = (current_index + 1) % len(ANIMATIONS)
            elif event.key_number == 1:  # DOWN
                new_index = (current_index - 1) % len(ANIMATIONS)
            else:
                return False
            
            print(f"Switching to {ANIMATIONS[new_index]}")
            microcontroller.nvm[0] = new_index
            supervisor.reload()
            return True
    except Exception as e:
        print(f"Button check failed: {e}")
    return False