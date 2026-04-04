# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This workspace contains two repositories for the **Thumby Color** handheld game console (RP2350-based, 128x128 RGB565 screen):

- **TinyCircuits-Tiny-Game-Engine/** — The game engine: a C module compiled into MicroPython firmware. Exposes 13 Python modules for graphics, audio, physics, input, animation, saves, and multiplayer.
- **TinyCircuits-Thumby-Color-Games/** — Community game collection. Each game is a self-contained directory with `main.py` + assets. Games are written in pure MicroPython.

## Hardware Specs

- **Display**: 128x128 pixels, 16-bit RGB565, GC9107 LCD, double-buffered
- **Buttons**: A, B, D-pad (UP/DOWN/LEFT/RIGHT), LB, RB, MENU
- **Audio**: 4 simultaneous channels, 22050Hz, WAV/RTTTL/procedural tones
- **Other**: Rumble motor, battery monitor, RTC, USB link multiplayer
- **Memory**: 520KB SRAM + 2MB flash scratch = ~2.6MB heap

## Build Commands

### Linux emulator build (primary development workflow)

Prerequisites: `sudo apt install libsdl2-dev libffi-dev build-essential`

Requires TinyCircuits MicroPython fork cloned as sibling at `../mp-thumby` (branch: `engine`, submodules initialized, mpy-cross built).

From `TinyCircuits-Tiny-Game-Engine/filesystem`:
```bash
# Build
(cd ../../ports/unix && make -j8 DEBUG=1 USER_C_MODULES=../../TinyCircuits-Tiny-Game-Engine)

# Run
../../ports/unix/build-standard/micropython -X heapsize=2617152 main.py

# Build + run combined
(cd ../../ports/unix && make -j8 DEBUG=1 USER_C_MODULES=../../TinyCircuits-Tiny-Game-Engine) && (../../ports/unix/build-standard/micropython main.py)

# Clean
(cd ../../ports/unix && make clean)
```

### RP2350 hardware build

Prerequisites: `sudo apt install git python3 cmake gcc-arm-none-eabi libnewlib-arm-none-eabi build-essential g++ libstdc++-arm-none-eabi-newlib`

From `TinyCircuits-Tiny-Game-Engine/`:
```bash
python3 build_and_upload.py
```
Output: `mp-thumby/ports/rp2/build-THUMBY_COLOR/firmware.uf2`

### Debugging crashes with gdb

From `TinyCircuits-Tiny-Game-Engine/filesystem`:
```bash
(cd ../../ports/unix && make -j8 DEBUG=1 USER_C_MODULES=../../TinyCircuits-Tiny-Game-Engine) && (gdb ../../ports/unix/build-standard/micropython main.py)
# In gdb: run main.py, then bt for backtrace after crash
```

## Engine Architecture

### C module structure (`TinyCircuits-Tiny-Game-Engine/src/`)

The engine is a single MicroPython C user module defined in `micropython.cmake` (~83 source files). Key subsystems:

| Directory | Purpose |
|-----------|---------|
| `nodes/` | Scene graph: `node_base.c` (hierarchy, layers, tick/draw), `physics_node_base.c` (velocity, collisions) |
| `nodes/2D/` | Sprite2D, Rectangle2D, Circle2D, Line2D, Text2D, GUI buttons, physics shapes |
| `nodes/3D/` | CameraNode (projection, viewport, zoom), MeshNode, VoxelSpaceNode |
| `draw/` | Rendering pipeline: pixel/line/rect/circle/blit/text, shaders, depth buffer |
| `display/` | Framebuffer management, `engine_display_driver_rp2_gc9107.c` (LCD driver) |
| `audio/` | 4-channel DMA audio, mixing |
| `resources/` | Loaders: TextureResource (BMP 1/4/8/16-bit), FontResource, WavSound, ToneSound, RTTTL, Mesh, Noise |
| `physics/` | 2D rigid body: rect-rect, circle-circle, rect-circle collision detection and resolution |
| `animation/` | Tween interpolation (30 easing functions), Delay timers |
| `io/` | Button state machine (press/release/long/double/autorepeat), rumble, battery |
| `save/` | Key-value persistent storage |
| `math/` | Vector2, Vector3, Matrix4x4, Rectangle |
| `link/` | USB multiplayer protocol |
| `time/` | RTC (BM8563 I2C) |

External libs (`lib/`): cglm (matrix math), FastNoiseLite (procedural noise), bm8563 (RTC driver).

### Rendering pipeline (per `engine_tick()`)

1. Update button states
2. Tick animation tweens/delays
3. Invoke all node `tick` callbacks
4. Remove nodes marked for destruction
5. Invoke all node `draw` callbacks
6. Process GUI input
7. Send back framebuffer to display, swap buffers
8. Clear framebuffer and depth buffer

### Node system

- Parent-child hierarchy: `add_child()`, `remove_child()`, `get_child()`, `get_child_count()`
- 256 render layers (higher = on top)
- Each node has `tick(dt)` and `draw(camera)` callbacks settable from Python
- Cleanup: `mark_destroy()`, `mark_destroy_children()`, `mark_destroy_all()`
- Node types enum in `node_types.h`: EMPTY=0, CAMERA=1, PHYSICS_RECT=2, PHYSICS_CIRCLE=3, RECT=4, LINE=5, CIRCLE=6, SPRITE=7, TEXT=8, VOXELSPACE=9, VOXELSPACE_SPRITE=10, MESH_3D=11, GUI_BUTTON=12, GUI_BITMAP_BUTTON=13

## MicroPython API Reference

### Game skeleton

```python
import engine_main          # MUST be first import — initializes hardware
import engine
from engine_nodes import CameraNode, Sprite2DNode, Text2DNode, Rectangle2DNode
from engine_resources import TextureResource, FontResource, WaveSoundResource
from engine_math import Vector2, Vector3
from engine_draw import Color
import engine_io
import engine_audio

engine.fps_limit(30)       # 30 or 60 typical; engine.disable_fps_limit() for uncapped
camera = CameraNode()      # Required — root of visible scene

# Load resources once at startup
tex = TextureResource("assets/sprite.bmp")
font = FontResource("assets/font.bmp")
sfx = WaveSoundResource("assets/hit.wav")

# Create nodes, add to camera
sprite = Sprite2DNode(texture=tex, position=Vector2(0, 0), layer=5)
camera.add_child(sprite)

while True:
    if engine.tick():      # Returns True when a frame should run
        dt = engine.dt()   # Delta time in seconds
        # Game logic here
```

### engine

- `tick()` → bool — run one frame, returns True if ticked (respects fps_limit)
- `start()` — blocking main loop (alternative to while/tick)
- `end()` — stop engine loop
- `dt()` → float — seconds since last tick
- `fps_limit(fps)` / `disable_fps_limit()` / `get_running_fps()`
- `freq(hz)` — get/set CPU frequency
- `reset(soft_reset=False)` — device reset
- `setting_volume(vol, save=False)` / `setting_brightness(val, save=False)` — 0.0-1.0

### engine_io

**Button objects**: `A`, `B`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `LB`, `RB`, `MENU`

Each button has:
- `is_pressed` — currently held
- `is_just_pressed` — became pressed this frame
- `is_just_released` — became released this frame
- `is_long_pressed` / `is_just_long_pressed` — held past `long_press_time` (default 400ms)
- `is_just_short_released` / `is_just_long_released` — released before/after long press
- `is_just_double_pressed` — double-tap detected within `double_press_time` (default 300ms)
- `press_time()` — current/last press duration in ms
- Configurable: `long_press_time`, `double_press_time`, `autorepeat_delay_time`, `autorepeat_interval_time`

**Other**:
- `rumble(intensity)` — 0.0-1.0
- `battery_voltage()` → float volts, `battery_level()` → 0.0-1.0
- `is_plugged_in()`, `is_charging()` → bool
- `indicator(value)` — set LED: bool/Color/int/None
- `gui_focused(bool)`, `gui_focused_toggle()`, `gui_wrapping(bool)`, `gui_passing(bool)`, `focused_node()`

### engine_nodes

**All nodes share**: `position`, `rotation`, `scale`, `opacity`, `visible`, `disabled`, `layer`, `tick(dt)` callback, `draw(camera)` callback, hierarchy methods.

**Sprite2DNode** — textured sprite with animation
- `texture` (TextureResource), `transparent_color` (Color)
- Sprite sheet: `frame_count_x`, `frame_count_y`, `frame_current_x`, `frame_current_y`
- Animation: `fps`, `playing` (bool), `loop` (bool)

**Rectangle2DNode** — `width`, `height`, `color`, `outline` (bool)

**Circle2DNode** — `radius`, `color`, `outline` (bool)

**Line2DNode** — `start`, `end`, `color`

**Text2DNode** — `text` (str), `font` (FontResource), `color`, `letter_spacing`, `line_spacing`, `width`/`height` (read-only calculated)

**EmptyNode** — container, no rendering

**CameraNode** — `position` (Vector3), `rotation` (Vector3), `zoom`, `fov`, `view_distance`, `viewport` (Rectangle)

**PhysicsRectangle2DNode** / **PhysicsCircle2DNode** — physics bodies with:
- `velocity` (Vector2), `angular_velocity`
- `density`, `friction`, `bounciness`, `gravity_scale` (Vector2)
- `dynamic` (bool), `solid` (bool)
- `collision_mask` (uint32), `on_collide` callback, `on_separate` callback
- Rectangle: `width`, `height`; Circle: `radius`

**GUIButton2DNode** / **GUIBitmapButton2DNode** — interactive buttons with focus-based D-pad navigation, state callbacks (`on_just_pressed_cb`, `on_focused_cb`, etc.)

**MeshNode** — 3D triangle mesh: `mesh` (MeshResource), `texture`, `color`

**VoxelSpaceNode** — terrain renderer: `texture_resource`, `heightmap_resource`, `lod`, `curvature`

### engine_draw

- `set_background_color(color)` / `set_background(texture)` — screen background
- `pixel(color, x, y, opacity)`, `line(color, x1, y1, x2, y2, opacity)`
- `rect(color, x, y, w, h, outline, opacity)`, `circle(color, x, y, radius, outline, opacity)`
- `text(font, text, color, x, y, letter_spacing, line_spacing, opacity)`
- `blit(texture, x, y, transparent_color, opacity)` — draw texture without camera transform
- `back_fb_data()` → bytearray, `back_fb()` → framebuf object — direct framebuffer access
- `update()` — force send framebuffer to display

**Color class**: `Color()`, `Color(rgb565_int)`, `Color(r, g, b)` with floats 0.0-1.0. Properties: `.r`, `.g`, `.b`, `.value`.

**Predefined colors**: `black`, `white`, `red`, `green`, `blue`, `cyan`, `magenta`, `yellow`, `orange`, `purple`, `pink`, `brown`, `gold`, `silver`, `skyblue`, `violet`, `navy`, `darkgreen`, `darkcyan`, `maroon`, `olive`, `lightgrey`, `darkgrey`, `greenyellow`

### engine_resources

- `TextureResource(path, in_ram=True)` — BMP 1/4/8/16-bit. Properties: `width`, `height`, `data` (bytearray), `bit_depth`, `colors` (palette)
- `TextureResource(width, height, 0, bit_depth)` — create empty texture for framebuffer rendering
- `FontResource(path)` — bitmap font (ASCII 32-126)
- `WaveSoundResource(path)` — WAV audio (8/16-bit PCM)
- `ToneSoundResource()` — procedural sine tone: `frequency` (Hz), `duration` (ms)
- `RTTTLSoundResource(path)` — Nokia ringtone format
- `MeshResource(path)` — 3D mesh data
- `NoiseResource()` — FastNoiseLite procedural noise

### engine_audio

- `play(sound_resource, channel, loop)` → AudioChannel — 4 channels (0-3)
- `stop(channel)` — stop playback
- `set_volume(vol)` / `get_volume()` — game volume (0.0+)

**AudioChannel**: `.source`, `.gain` (0.0-1.0), `.time`, `.amplitude`, `.loop`, `.done`, `.stop()`

### engine_animation

**Tween**: `tween = Tween()`, then `tween.start(object, "attr_name", start_val, end_val, duration_ms, speed, loop_type, ease_type)`. Start value can be `None` (use current). Properties: `.paused`, `.finished`, `.during` (per-tick callback), `.after` (completion callback), `.speed`.

**Delay**: `delay = Delay()`, then `delay.start(duration_ms, callback)`. Properties: `.finished`, `.after`.

**Loop types**: `ONE_SHOT`, `LOOP`, `PING_PONG`

**Easing functions** (30 total): `EASE_LINEAR`, plus `_IN`, `_OUT`, `_IN_OUT` variants for: `SINE`, `QUAD`, `CUBIC`, `QUART`, `QUINT`, `EXP`, `CIRC`, `BACK`, `ELAST`, `BOUNCE`

### engine_physics

- `set_gravity(x, y)` / `get_gravity()` → Vector2
- Collision handling via `PhysicsRectangle2DNode` / `PhysicsCircle2DNode` with `on_collide` / `on_separate` callbacks receiving `CollisionContact2D`

### engine_save

- `set_location(filepath)` — set save file (relative path)
- `save(entry_name, value)` / `load(entry_name, default=None)` — supports str, int, float, bytearray, Vector2, Vector3, Color
- `delete(entry_name)` / `delete_location()` — cleanup

### engine_math

- `Vector2(x=0, y=0)` — `.x`, `.y` (float, settable)
- `Vector3(x=0, y=0, z=0)` — `.x`, `.y`, `.z` (float, settable)
- `Rectangle(x, y, width, height)` — `.x`, `.y`, `.width`, `.height`
- `Matrix4x4` — 4x4 transform matrix

### engine_link (multiplayer)

- `start()` / `stop()` — enable/disable USB link mode
- `connected()` → bool, `is_host()` → bool
- `send(bytearray, count, offset)` → int, `read(count)` → bytearray, `read_into(buf, count, offset)` → int
- `available()` → int, `clear_send()`, `clear_read()`
- `set_connected_cb(fn)`, `set_disconnected_cb(fn)`

### engine_time (RTC)

- `datetime(tuple=None)` — get/set: `(year, month, mday, hour, min, sec, wday, yday)`
- `is_compromised()` → bool — True if RTC lost power

## Game Development Patterns

### Game directory structure
```
MyGame/
├── main.py                  # Entry point
├── assets/
│   ├── sprites/             # .bmp textures (1/4/8/16-bit)
│   ├── sound/               # .wav files
│   └── font/                # .bmp font atlases
├── arcade_description.txt   # Short description for arcade listing
└── icon.bmp                 # Game icon
```

### State machine pattern
```python
SM_TITLE = const(0)
SM_PLAYING = const(1)
SM_GAMEOVER = const(2)
state = SM_TITLE

while True:
    if engine.tick():
        if state == SM_TITLE:
            if engine_io.A.is_just_pressed:
                state = SM_PLAYING
        elif state == SM_PLAYING:
            # game logic
```

### Page pattern (multi-screen games)
```python
class GamePage:
    def __init__(self):
        self.loaded = False
    
    @micropython.native
    def preload(self):
        if not self.loaded:
            self.loaded = True
            self.tex = TextureResource("sprite.bmp")
    
    def start(self):
        cam = CameraNode()
        while True:
            if engine.tick():
                if should_exit: break
```

### Framebuffer rendering (custom pixel-level drawing)
```python
import framebuf
screen = TextureResource(128, 128, 0, 16)
fbuf = framebuf.FrameBuffer(screen.data, 128, 128, framebuf.RGB565)
fbuf.fill(0)
fbuf.rect(x, y, w, h, color, True)
sprite = Sprite2DNode(texture=screen)

# Viper-optimized pixel access:
@micropython.viper
def fast_draw(data):
    buf = ptr16(data)
    buf[x + (y << 7)] = color_rgb565
```

### Subclassing nodes
```python
class Player(Sprite2DNode):
    def __init__(self, texture):
        super().__init__(self)
        self.texture = texture
        self.frame_count_x = 4
        self.hp = 100
    
    def tick(self, dt):
        if engine_io.RIGHT.is_pressed:
            self.position.x += 60 * dt
```

### Performance decorators
- `@micropython.native` — JIT compilation, ~2x speedup for compute-heavy functions
- `@micropython.viper` — near-C speed with typed pointers (`ptr8`, `ptr16`, `ptr32`), ~10x speedup for pixel operations

### Memory management
- Call `gc.collect()` after destroying many nodes or loading resources
- Use `mark_destroy()` to clean up nodes (processed at end of tick)
- Load large textures with `engine.tick()` calls between them to avoid memory exhaustion
- `gc.mem_free()` / `gc.mem_alloc()` for profiling

### Audio conventions
- Channel 0-2: SFX (non-looping)
- Channel 3: BGM (looping, lower gain ~0.15-0.3)
- Play BGM: `ch = engine_audio.play(music, 3, True); ch.gain = 0.2`

## Discovered Gotchas

### engine.dt() is unreliable in manual tick loops
`engine.dt()` measures time since the last tick *started*, so calling it right after `engine.tick()` returns near-zero. Games using node tick callbacks (`def tick(self, dt)`) get correct dt from the engine. For manual loops, compute dt yourself:
```python
import time
_last_ms = time.ticks_ms()
while True:
    if engine.tick():
        _now_ms = time.ticks_ms()
        dt = time.ticks_diff(_now_ms, _last_ms) * 0.001
        _last_ms = _now_ms
```

### Sprite2DNode has NO `visible` attribute
Use `opacity = 0.0` to hide, `opacity = 1.0` to show. Move off-screen (`position.x = -200`) as extra safety for hidden nodes.

### mp_vprintf assertion in DEBUG builds
The engine's debug prints trigger `mp_vprintf: Assertion 'unsupported fmt char'` in MicroPython DEBUG builds. Fix: build with `CFLAGS_EXTRA="-DNDEBUG"`:
```bash
make -j8 DEBUG=1 USER_C_MODULES=../../TinyCircuits-Tiny-Game-Engine CFLAGS_EXTRA="-DNDEBUG"
```

### BMP format requirements
- Must be standard bottom-up format (positive height in header)
- 16-bit RGB565 with BI_BITFIELDS compression (type 3) and R/G/B masks
- Negative height (top-down) loads but reports negative dimensions, causing crashes
- Black pixels (0,0,0) in sprites are kept as-is; use magenta (0xF81F) for transparency
- Grey background from spritesheets must be converted to magenta

### CameraNode coordinate system
Default `CameraNode()` at position (0,0,0). Sprites use camera coords: -64 to +64 maps to screen 0-127. `engine_draw.text()` and `engine_draw.rect()` use screen coords (0-127) directly, NOT camera coords. Mix carefully.

### Sprite animation auto-plays through Y frames
If `frame_count_y > 1` and `playing = True`, the engine advances through ALL frames (X then Y). Set `playing = False` on sprite sheets where Y axis selects a type/variant, not animation frames.

### Node pool pattern (no create/destroy during gameplay)
Creating/destroying Sprite2DNodes during gameplay causes GC pressure. Pre-allocate a pool at startup, toggle `opacity` to show/hide, reuse by reassigning `frame_current_x/y` and `position`.

## Device Connection & Upload

### USB connection (WSL2)
The Thumby Color appears as USB serial `VID:PID=2E8A:0005`. In WSL2, USB doesn't pass through automatically:

```powershell
# Windows PowerShell (Admin) — install once:
winget install usbipd

# Each session — bind and attach:
usbipd list                          # Find the 2E8A:0005 device
usbipd bind --busid <BUSID>         # e.g. 1-6
usbipd attach --wsl --busid <BUSID>
```

**Important**: Close Thonny/any Windows app using the COM port BEFORE running `usbipd attach`.

After attach, the device appears as `/dev/ttyACM0` in WSL.

### Upload games to device
Use `mpremote` (install: `pip3 install mpremote pyserial`):
```bash
# Quick upload — use the deploy script:
./deploy.sh Thumbalaga

# Manual upload:
mpremote connect /dev/ttyACM0 mkdir :Games/MyGame
mpremote connect /dev/ttyACM0 cp main.py :Games/MyGame/main.py
mpremote connect /dev/ttyACM0 reset
```

### Thonny IDE (Windows, no WSL needed)
1. Set interpreter: **MicroPython (Raspberry Pi Pico)**, port auto-detect
2. Click the **red stop button** to connect (interrupts running game)
3. **View → Files** to browse device filesystem
4. Right-click folder → **Upload to /Games**

### Firmware update (only if engine C code changes)
```bash
# Build (WSL, needs gcc-arm-none-eabi):
cd /home/maustin/mp-thumby/TinyCircuits-Tiny-Game-Engine
python3 build_and_upload.py no_upload
# Output: ../ports/rp2/build-THUMBY_COLOR/firmware.uf2
```
1. Enter BOOTSEL: turn OFF → hold DOWN dpad → turn ON
2. Device mounts as RP2350 drive in Windows — copy .uf2 to it
3. After reboot, update system files via mpremote if engine version changed:
```bash
mpremote connect /dev/ttyACM0 cp filesystem/main.py :main.py
mpremote connect /dev/ttyACM0 cp -r filesystem/system :system
```

### Cable requirements
Must be a USB-C **data cable**, not charge-only. If device doesn't appear in `usbipd list` or Device Manager, try a different cable.

## Emulator vs Device Differences

| Aspect | Linux Emulator | RP2350 Device |
|--------|---------------|---------------|
| Input | Keyboard (W/A/S/D=dpad, .=A, ,=B, Shift=LB, Space=RB, Enter=Menu) | Physical buttons |
| Audio | SDL2 audio | PWM + DMA |
| Display | SDL2 window (3x scaled) | GC9107 SPI LCD |
| Performance | Much faster than device | Constrained, optimize hot paths |
| Rumble | No-op | PWM motor |
| Battery | No-op | ADC monitoring |

## External Resources

- [Engine Documentation](https://color.thumby.us/doc/landing.html)
- [Arcade (download games)](https://color.thumby.us/code/arcade)
- [MicroPython Code Editor](https://color.thumby.us/code/)
- [Getting Started with Thonny](https://color.thumby.us/pages/getting-started-with-thonny/getting-started-with-thonny/)
- [Firmware Updates](https://color.thumby.us/pages/firmware-and-updating/firmware-and-updating/)
