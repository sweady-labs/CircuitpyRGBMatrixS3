"""
LED Matrix Control - Web Server + Non-Blocking Animations
Web server ALWAYS responsive. Animations update frame-by-frame.
You can change animations in real-time.
"""
import microcontroller
import time
import board
import displayio

ANIMATIONS = ["bouncing_balls", "breathing", "cap-shield", "dna", "fireworks", "game_of_life",
              "ironman", "kaleidoscope", "matrix_rain", "moving-lines", "plasma", "rain",
              "scrolling_text", "warp", "strange_things", "christmas", "tetris"]

MAX_ANIMATION_TIME = 18000  # 5 hours
FRAME_TIME = 0.03  # 33ms per frame = ~30 FPS

print("\n" + "="*60)
print("LED Matrix - Non-Blocking Web + Animations")
print("="*60)

# Initialize NVM
try:
    current_anim_idx = microcontroller.nvm[0]
    if current_anim_idx >= len(ANIMATIONS):
        current_anim_idx = 0
        microcontroller.nvm[0] = 0
except:
    current_anim_idx = 0
    microcontroller.nvm[0] = 0

# Animation engine state
animation_module = None
animation_state = None
animation_start_time = None
animation_running = False
should_load_animation = False
next_frame_time = 0

def load_animation_module(anim_name):
    """Load animation module - doesn't start it yet"""
    global animation_module
    try:
        import sys
        import gc
        
        module_name = "led_sequences.%s" % anim_name
        print("[LOAD] Clearing cache for %s" % module_name)
        
        # Clear from sys.modules to force fresh import
        if module_name in sys.modules:
            del sys.modules[module_name]
        if "led_sequences" in sys.modules:
            del sys.modules["led_sequences"]
        
        # Force garbage collection
        gc.collect()
        
        print("[LOAD] Starting import of %s" % module_name)
        
        # Try using importlib if available
        try:
            import importlib
            print("[LOAD] Using importlib.import_module")
            animation_module = importlib.import_module(module_name)
        except (ImportError, AttributeError):
            print("[LOAD] importlib not available, using __import__")
            # CircuitPython: __import__ doesn't support keyword args
            # Use positional args: __import__(name, globals, locals, fromlist, level)
            animation_module = __import__(module_name, None, None, [anim_name], 0)
        
        print("[LOAD] Module loaded successfully")
        print("[LOAD] Module type: %s" % str(type(animation_module)))
        
        # List all functions in module
        funcs = [x for x in dir(animation_module) if not x.startswith('_')]
        print("[LOAD] Module contents: %s" % str(funcs)[:100])
        
        has_init = hasattr(animation_module, 'init_animation')
        has_update = hasattr(animation_module, 'update_animation')
        
        print("[LOAD] Has init_animation: %s" % str(has_init))
        print("[LOAD] Has update_animation: %s" % str(has_update))
        
        if has_init and has_update:
            print("Animation loaded: %s (READY)" % anim_name)
            return True
        else:
            print("ERROR: Animation %s missing functions!" % anim_name)
            return False
            
    except Exception as e:
        print("Error loading animation: %s" % str(e))
        try:
            import traceback
            # CircuitPython may not have print_exc, so catch that too
            traceback.print_exc()
        except:
            print("(traceback unavailable)")
        animation_module = None
        return False

def start_animation(anim_name):
    """Start animation (initialize state)"""
    global animation_module, animation_state, animation_start_time, animation_running
    
    if load_animation_module(anim_name):
        try:
            # Call init function if it exists
            if hasattr(animation_module, 'init_animation'):
                animation_state = animation_module.init_animation()
                animation_start_time = time.time()
                animation_running = True
                print("Animation started: %s" % anim_name)
                return True
            else:
                # Old-style animation - will block
                print("Animation is old-style (blocking) - loading anyway")
                animation_start_time = time.time()
                animation_running = True
                return True
        except Exception as e:
            print("Error starting animation: %s" % str(e))
    
    animation_running = False
    return False

def update_animation_frame():
    """Update animation by ONE frame - called from main loop"""
    global animation_module, animation_state, animation_running, animation_start_time
    
    if not animation_running:
        return False
    
    # Check timeout
    if time.time() - animation_start_time > MAX_ANIMATION_TIME:
        print("Animation timeout reached")
        stop_animation()
        return False
    
    try:
        # Call update function to draw ONE frame
        if hasattr(animation_module, 'update_animation'):
            animation_state = animation_module.update_animation(animation_state)
            return True
        else:
            # Old-style animation - let it run (will block)
            # This is the fallback for animations that haven't been refactored
            return True
    except Exception as e:
        print("Animation error: %s" % str(e))
        stop_animation()
        return False

def stop_animation():
    """Stop animation"""
    global animation_module, animation_state, animation_running, animation_start_time
    animation_module = None
    animation_state = None
    animation_running = False
    animation_start_time = None
    try:
        displayio.release_displays()
    except:
        pass

# Start web server
try:
    import wifi
    import socketpool
    from adafruit_httpserver import JSONResponse, Request, Response, Server
    
    print("WEB SERVER MODE\n")
    
    # Parse settings
    settings = {}
    try:
        with open("/settings.toml") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"')
                    settings[k] = v
    except:
        print("Warning: Could not parse settings.toml")
    
    # WiFi
    ssid = settings.get("CIRCUITPY_WIFI_SSID", "")
    pwd = settings.get("CIRCUITPY_WIFI_PASSWORD", "")
    
    if ssid:
        print("WiFi: Connecting to %s..." % ssid)
        try:
            wifi.radio.connect(ssid, pwd)
            ip = str(wifi.radio.ipv4_address)
            print("WiFi: OK - %s\n" % ip)
        except Exception as e:
            print("WiFi error: %s\n" % str(e))
            ip = "0.0.0.0"
    else:
        print("WiFi: SSID not configured\n")
        ip = "0.0.0.0"
    
    # Create server
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, debug=False)
    
    @server.route("/")
    def root(request: Request):
        try:
            with open("/web/index.html", "r") as f:
                content = f.read()
                return Response(request, content, content_type="text/html")
        except Exception as e:
            print("Root error: %s" % str(e))
            return Response(request, "<h1>LED Matrix</h1><p>Error loading page</p>", content_type="text/html")
    
    @server.route("/api/current")
    def get_current(request: Request):
        idx = microcontroller.nvm[0]
        if idx >= len(ANIMATIONS):
            idx = 0
        return JSONResponse(request, {
            "index": idx,
            "name": ANIMATIONS[idx],
            "is_playing": animation_running
        })
    
    @server.route("/api/animations")
    def get_animations(request: Request):
        return JSONResponse(request, {"animations": ANIMATIONS})
    
    @server.route("/api/set", ["POST"])
    def set_animation(request: Request):
        try:
            data = request.json()
            name = data.get("name", "")
            if name in ANIMATIONS:
                idx = ANIMATIONS.index(name)
                microcontroller.nvm[0] = idx
                print("Selected: %s" % name)
                return JSONResponse(request, {"ok": True, "name": name, "index": idx})
        except Exception as e:
            print("Set error: %s" % str(e))
        return JSONResponse(request, {"ok": False, "error": "Invalid animation"})
    
    @server.route("/api/load-animation", ["POST"])
    def api_load_animation(request: Request):
        global should_load_animation
        try:
            idx = microcontroller.nvm[0]
            if idx >= len(ANIMATIONS):
                idx = 0
            anim_name = ANIMATIONS[idx]
            
            should_load_animation = True
            print("Queued: %s" % anim_name)
            return JSONResponse(request, {"ok": True, "queued": anim_name})
        except Exception as e:
            print("Error: %s" % str(e))
            return JSONResponse(request, {"ok": False, "error": str(e)})
    
    @server.route("/api/stop-animation", ["POST"])
    def api_stop_animation(request: Request):
        global animation_running
        if animation_running:
            stop_animation()
            print("Animation stopped")
            return JSONResponse(request, {"ok": True, "status": "stopped"})
        return JSONResponse(request, {"ok": True, "status": "not_running"})
    
    @server.route("/api/status")
    def get_status(request: Request):
        if animation_running and animation_start_time:
            elapsed = time.time() - animation_start_time
            remaining = MAX_ANIMATION_TIME - elapsed
            return JSONResponse(request, {
                "status": "playing",
                "elapsed": int(elapsed),
                "remaining": max(0, int(remaining))
            })
        else:
            return JSONResponse(request, {"status": "idle"})
    
    server.start(ip, 80)
    print("HTTP: Ready on http://%s/" % ip)
    print("Available endpoints:")
    print("  GET  /api/current")
    print("  GET  /api/animations")
    print("  GET  /api/status")
    print("  POST /api/set")
    print("  POST /api/load-animation")
    print("  POST /api/stop-animation")
    print("\nWEB SERVER STAYS RESPONSIVE - animations update every frame!\n")
    
    # Main loop - ALWAYS responsive
    frame_count = 0
    while True:
        # If animation should load, start it
        if should_load_animation:
            should_load_animation = False
            idx = microcontroller.nvm[0]
            if idx >= len(ANIMATIONS):
                idx = 0
            anim_name = ANIMATIONS[idx]
            
            print("\n" + "="*60)
            print("Starting animation: %s" % anim_name)
            print("="*60 + "\n")
            
            start_animation(anim_name)
        
        # Update animation frame (non-blocking)
        current_time = time.time()
        if animation_running and current_time >= next_frame_time:
            update_animation_frame()
            next_frame_time = current_time + FRAME_TIME
            frame_count += 1
        
        # Always keep server responsive
        try:
            server.poll()
        except Exception as e:
            print("Server error: %s" % str(e))
        
        time.sleep(0.01)  # Small sleep to prevent CPU spinning

except Exception as e:
    print("STARTUP ERROR: %s" % str(e))
    try:
        import traceback
        traceback.print_exc()
    except:
        print("(traceback unavailable)")
    time.sleep(5)
