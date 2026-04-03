import engine_main

import engine
import engine_io
import engine_draw
import engine_audio
from engine_nodes import CameraNode, Sprite2DNode
from engine_resources import TextureResource, WaveSoundResource
from engine_math import Vector2
from engine_draw import Color
import random
import gc
import time

from constants import *
from player import Player
from enemy import Enemy
from formation import Formation
from bullets import BulletManager
from stars import Starfield
from explosions import ExplosionManager
from hud import HUD
from dive import update_diving_enemy, maybe_trigger_dive, start_dive
from entry_patterns import EntryState, get_entry_pattern, update_entry
from collision import (check_player_bullets_vs_enemies,
                       check_enemy_bullets_vs_player,
                       check_divers_vs_player)
from transforms import TransformManager, TRANSFORM_INDIVIDUAL_PTS
from popups import ScorePopups
from level import LevelData
from challenge import ChallengeState, update_challenge, CHALLENGE_HIT_POINTS, CHALLENGE_PERFECT_BONUS, CHALLENGE_TOTAL, CHALLENGE_ENEMIES_PER_WAVE

# ── Setup ───────────────────────────────────────────────────
engine.fps_limit(60)

camera = CameraNode()  # Default position (0, 0, 0) — sprites use -64 to +64
engine_draw.set_background_color(Color(COL_BLACK))


# ── Loading screen with logo ───────────────────────────────
_load_count = 0
_load_total = 20  # approximate number of resources to load

def _draw_loading(fb_ref=None):
    global _load_count
    _load_count += 1
    engine.tick()
    fb = engine_draw.back_fb()
    # Draw loading bar at bottom
    bar_y = 115
    bar_h = 6
    bar_x = 20
    bar_w = 88
    progress = min(_load_count / _load_total, 1.0)
    fb.rect(bar_x, bar_y, bar_w, bar_h, COL_WHITE, False)  # outline
    fill_w = int((bar_w - 2) * progress)
    if fill_w > 0:
        fb.rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2, COL_CYAN, True)  # fill
    engine_draw.text(None, "LOADING", None, 40, 104, 1, 0, 1.0)


# Show logo
try:
    _logo_tex = TextureResource("assets/logo.bmp")
    _logo_node = Sprite2DNode()
    _logo_node.texture = _logo_tex
    _logo_node.transparent_color = transparent
    _logo_node.position.x = 0
    _logo_node.position.y = 0
    _logo_node.layer = 20
    camera.add_child(_logo_node)
    engine.tick()
except:
    _logo_node = None

_draw_loading()


# ── Load resources ──────────────────────────────────────────
def load_tex(path):
    _draw_loading()
    return TextureResource(path)


player_tex = load_tex("assets/player.bmp")
enemy_tex = load_tex("assets/enemies.bmp")
explosion_tex = load_tex("assets/explosion.bmp")
player_exp_tex = load_tex("assets/player_explosion.bmp")
captured_tex = load_tex("assets/player_captured.bmp")

# Load sounds — None if file missing
def load_sfx(path):
    _draw_loading()
    try:
        return WaveSoundResource(path)
    except:
        return None

shoot_sfx = load_sfx("assets/shoot.wav")
explode_bee_sfx = load_sfx("assets/explode.wav")
explode_butterfly_sfx = load_sfx("assets/explode2.wav")
explode_boss_hit_sfx = load_sfx("assets/explode3.wav")  # non-fatal boss hit
explode_boss_sfx = load_sfx("assets/explode_boss.wav")   # boss kill + transforms
beam_capture_sfx = load_sfx("assets/beam_capture.wav")    # beam with capture
die_sfx = load_sfx("assets/player_die.wav")
dive_sfx = load_sfx("assets/dive.wav")
beam_sfx = load_sfx("assets/beam.wav")
capture_sfx = load_sfx("assets/capture.wav")
transform_sfx = load_sfx("assets/transform.wav")
extra_life_sfx = load_sfx("assets/extra_life.wav")
rescue_sfx = load_sfx("assets/rescue.wav")
enemy_shot_sfx = load_sfx("assets/enemy_shot.wav")
level_start_sfx = load_sfx("assets/level_start.wav")
challenge_start_sfx = load_sfx("assets/challenge_start.wav")
challenge_over_sfx = load_sfx("assets/challenge_over.wav")
challenge_perfect_sfx = load_sfx("assets/challenge_perfect.wav")

transparent = Color(COL_MAGENTA)


# ── Create player ───────────────────────────────────────────
player = Player(player_tex)
camera.add_child(player)

# Wingman node — appears next to player in dual fighter mode
wingman_node = Sprite2DNode()
wingman_node.texture = player_tex
wingman_node.transparent_color = transparent
wingman_node.opacity = 0.0
wingman_node.layer = 10
camera.add_child(wingman_node)

WINGMAN_OFFSET_X = const(10)  # how far right the wingman sits


# ── Create enemy node pool ──────────────────────────────────
enemy_nodes = []
for i in range(FORM_COLS * FORM_ROWS):
    engine.tick()
    node = Sprite2DNode()
    node.texture = enemy_tex
    node.transparent_color = transparent
    node.frame_count_x = ENEMY_FRAMES  # 8 rotation frames
    node.frame_count_y = NUM_ENEMY_TYPES  # 8 enemy types
    node.frame_current_x = IDLE_FRAME_A
    node.frame_current_y = 0
    node.playing = False
    node.loop = False
    node.opacity = 0.0
    node.position.x = -200
    node.position.y = -200
    node.layer = 5
    camera.add_child(node)
    enemy_nodes.append(node)


# ── Create explosion node pool ──────────────────────────────
explosion_nodes = []
for i in range(MAX_EXPLOSIONS):
    node = Sprite2DNode()
    node.texture = explosion_tex
    node.transparent_color = transparent
    node.frame_count_x = EXPLOSION_FRAMES
    node.frame_count_y = 1
    node.fps = EXPLOSION_FPS
    node.playing = False
    node.loop = False
    node.opacity = 0.0
    node.layer = 15
    camera.add_child(node)
    explosion_nodes.append(node)

# Player explosion node (separate, uses same explosion sheet)
player_exp_node = Sprite2DNode()
player_exp_node.texture = player_exp_tex
player_exp_node.transparent_color = transparent
player_exp_node.frame_count_x = 4  # player explosion has 4 frames (section 2)
player_exp_node.frame_count_y = 1
player_exp_node.fps = EXPLOSION_FPS
player_exp_node.playing = False
player_exp_node.loop = False
player_exp_node.opacity = 0.0
player_exp_node.layer = 16
camera.add_child(player_exp_node)

# Captured ship node — red version, shown held by boss
captured_ship_node = Sprite2DNode()
captured_ship_node.texture = captured_tex
captured_ship_node.transparent_color = transparent
captured_ship_node.opacity = 0.0
captured_ship_node.layer = 6
camera.add_child(captured_ship_node)

# Track which boss holds a captured ship (None = no captured ship)
capturing_boss = None

# Rescue animation state
rescue_active = False
rescue_timer = 0.0
rescue_start_x = 0.0
rescue_start_y = 0.0
RESCUE_DURATION = 1.5  # seconds for ship to fly down to player


def capture_player_ship(boss_enemy):
    """Boss captures the player's ship."""
    global capturing_boss
    capturing_boss = boss_enemy
    captured_ship_node.opacity = 1.0
    captured_ship_node.texture = captured_tex  # red


def release_captured_ship():
    """Release captured ship (boss died or game reset)."""
    global capturing_boss, rescue_active
    capturing_boss = None
    rescue_active = False
    captured_ship_node.opacity = 0.0
    captured_ship_node.position.x = -200
    captured_ship_node.position.y = -200


def start_rescue():
    """Begin rescue animation — ship flies from boss position to player."""
    global rescue_active, rescue_timer, rescue_start_x, rescue_start_y, capturing_boss
    rescue_active = True
    rescue_timer = 0.0
    rescue_start_x = captured_ship_node.position.x
    rescue_start_y = captured_ship_node.position.y
    captured_ship_node.texture = player_tex  # back to white
    captured_ship_node.rotation = 0
    capturing_boss = None  # no longer held by boss


def update_rescue(dt):
    """Animate rescued ship flying down. Returns True when complete."""
    global rescue_timer, rescue_active
    if not rescue_active:
        return False

    rescue_timer += dt
    t = min(rescue_timer / RESCUE_DURATION, 1.0)

    # Fly from boss position down to wingman position beside player
    target_x = player.position.x + WINGMAN_OFFSET_X
    target_y = player.position.y
    captured_ship_node.position.x = rescue_start_x + (target_x - rescue_start_x) * t
    captured_ship_node.position.y = rescue_start_y + (target_y - rescue_start_y) * t
    captured_ship_node.opacity = 1.0

    if t >= 1.0:
        # Rescue complete — activate dual fighter
        rescue_active = False
        captured_ship_node.opacity = 0.0
        captured_ship_node.position.x = -200
        player.rescue_ship()
        wingman_node.opacity = 1.0
        wingman_node.position.x = player.position.x + WINGMAN_OFFSET_X
        wingman_node.position.y = player.position.y
        return True

    return False


# ── Hostile captured fighter ───────────────────────────────
# When boss holding captured ship is killed in formation,
# the red fighter becomes an autonomous enemy that dives and shoots.
# If killed → destroyed. If survives → joins next stage behind a boss.
import math as _math

hostile_fighter_active = False
hostile_fighter_alive = False
hostile_fighter_carry = False  # carry to next stage
hostile_fighter_x = 0.0
hostile_fighter_y = 0.0
hostile_fighter_start_x = 0.0
hostile_fighter_start_y = 0.0
hostile_fighter_dive_t = 0.0
hostile_fighter_fire_timer = 0.0
hostile_fighter_path = None


def activate_hostile_fighter(x, y):
    """Turn captured ship into hostile autonomous enemy at given position."""
    global hostile_fighter_active, hostile_fighter_alive
    global hostile_fighter_x, hostile_fighter_y, hostile_fighter_dive_t
    global hostile_fighter_fire_timer, hostile_fighter_path, hostile_fighter_carry
    hostile_fighter_active = True
    hostile_fighter_alive = True
    hostile_fighter_carry = False
    hostile_fighter_x = x
    hostile_fighter_y = y
    hostile_fighter_dive_t = 0.0
    hostile_fighter_fire_timer = 1.0 + random.random()
    hostile_fighter_path = None  # stays in formation initially
    captured_ship_node.texture = captured_tex  # red
    captured_ship_node.opacity = 1.0
    captured_ship_node.position.x = x
    captured_ship_node.position.y = y
    captured_ship_node.rotation = 0


def start_hostile_dive():
    """Start the hostile fighter diving."""
    global hostile_fighter_dive_t, hostile_fighter_path, hostile_fighter_start_x, hostile_fighter_start_y
    from dive import DIVE_CENTER, DIVE_SWEEP_LEFT, DIVE_SWEEP_RIGHT
    hostile_fighter_dive_t = 0.0
    hostile_fighter_start_x = hostile_fighter_x
    hostile_fighter_start_y = hostile_fighter_y
    hostile_fighter_path = random.choice([DIVE_CENTER, DIVE_SWEEP_LEFT, DIVE_SWEEP_RIGHT])


def kill_hostile_fighter():
    """Permanently destroy the hostile fighter."""
    global hostile_fighter_active, hostile_fighter_alive, hostile_fighter_carry
    hostile_fighter_active = False
    hostile_fighter_alive = False
    hostile_fighter_carry = False
    captured_ship_node.opacity = 0.0
    captured_ship_node.position.x = -200
    captured_ship_node.position.y = -200


def update_hostile_fighter(dt, bullet_mgr, player_x):
    """Update hostile fighter behavior. Returns 'hit_player' if it hits the player."""
    global hostile_fighter_x, hostile_fighter_y, hostile_fighter_dive_t
    global hostile_fighter_fire_timer, hostile_fighter_active, hostile_fighter_carry

    if not hostile_fighter_active or not hostile_fighter_alive:
        return None

    # If no dive path, wait briefly then start diving
    if hostile_fighter_path is None:
        hostile_fighter_fire_timer -= dt
        if hostile_fighter_fire_timer <= 0:
            start_hostile_dive()
        captured_ship_node.position.x = hostile_fighter_x
        captured_ship_node.position.y = hostile_fighter_y
        return None

    # Advance along dive path
    hostile_fighter_dive_t += dt * 0.5  # moderate speed

    path = hostile_fighter_path
    seg_count = len(path) - 1

    if hostile_fighter_dive_t >= 1.0:
        # Exited screen — carry to next stage
        hostile_fighter_active = False
        hostile_fighter_carry = True  # will rejoin next stage
        captured_ship_node.opacity = 0.0
        captured_ship_node.position.x = -200
        return None

    t_scaled = hostile_fighter_dive_t * seg_count
    seg_idx = int(t_scaled)
    seg_t = t_scaled - seg_idx
    if seg_idx >= seg_count:
        seg_idx = seg_count - 1
        seg_t = 1.0

    x0, y0 = path[seg_idx]
    x1, y1 = path[seg_idx + 1]
    hostile_fighter_x = hostile_fighter_start_x + x0 + (x1 - x0) * seg_t
    hostile_fighter_y = hostile_fighter_start_y + y0 + (y1 - y0) * seg_t

    # Clamp to screen
    hostile_fighter_x = max(-60, min(60, hostile_fighter_x))

    captured_ship_node.position.x = hostile_fighter_x
    captured_ship_node.position.y = hostile_fighter_y

    # Fire bullets while diving
    hostile_fighter_fire_timer -= dt
    if hostile_fighter_fire_timer <= 0:
        hostile_fighter_fire_timer = 0.8 + random.random() * 0.5
        bullet_mgr.fire_enemy(hostile_fighter_x, hostile_fighter_y, player_x)

    return None


hostile_fighter_entry_timer = 0.0
hostile_fighter_entry_target_boss = None


def attach_hostile_to_boss(formation_obj):
    """Set up the carried hostile fighter to fly in and attach to a boss."""
    global hostile_fighter_carry, hostile_fighter_active, hostile_fighter_alive
    global hostile_fighter_entry_timer, hostile_fighter_entry_target_boss

    if not hostile_fighter_carry:
        return

    # Find the first alive boss
    target = None
    for e in formation_obj.enemies:
        if e is not None and e.alive and (e.type == ENEMY_BOSS or e.type == ENEMY_BOSS_HIT):
            target = e
            break

    if target is None:
        hostile_fighter_carry = False
        return

    # Set up entry animation — will fly in from top after entry pattern finishes
    hostile_fighter_entry_target_boss = target
    hostile_fighter_entry_timer = 7.0  # delay: fly in after normal entry (~6s)
    hostile_fighter_carry = False
    hostile_fighter_active = False
    hostile_fighter_alive = False

    # Position off-screen at top
    captured_ship_node.texture = captured_tex
    captured_ship_node.opacity = 0.0
    captured_ship_node.position.x = 0
    captured_ship_node.position.y = -80


def update_hostile_entry(dt, formation_obj):
    """Animate the carried fighter flying in to attach behind a boss."""
    global hostile_fighter_entry_timer, hostile_fighter_entry_target_boss
    global capturing_boss

    if hostile_fighter_entry_target_boss is None:
        return

    hostile_fighter_entry_timer -= dt
    if hostile_fighter_entry_timer > 0:
        return  # still waiting for normal entry to finish

    boss = hostile_fighter_entry_target_boss
    if not boss.alive:
        hostile_fighter_entry_target_boss = None
        return

    # Fly from top of screen to above the boss
    t = min((-hostile_fighter_entry_timer) / 1.5, 1.0)  # 1.5s fly-in
    target_x = boss.node.position.x
    target_y = boss.node.position.y - 12

    captured_ship_node.opacity = 1.0
    captured_ship_node.position.x = target_x * t  # approach from center-top
    captured_ship_node.position.y = -70 + (target_y + 70) * t

    if t >= 1.0:
        # Arrived — attach to boss
        capturing_boss = boss
        captured_ship_node.position.x = target_x
        captured_ship_node.position.y = target_y
        hostile_fighter_entry_target_boss = None


# Tractor beam — procedurally drawn fan, no sprite node
# Beam colors (RGB565): alternating cyan/blue lines like original
BEAM_COL_1 = const(0x07FF)  # cyan
BEAM_COL_2 = const(0x001F)  # blue
BEAM_COL_3 = const(0x04FF)  # teal

BEAM_PHASE_INACTIVE = const(0)
BEAM_PHASE_EXPAND = const(2)
BEAM_PHASE_ACTIVE = const(3)
BEAM_PHASE_RETRACT = const(4)
BEAM_PHASE_CAPTURE = const(5)  # ship being pulled up
BEAM_PHASE_RETURN = const(6)   # boss flying back to formation

beam_phase = BEAM_PHASE_INACTIVE
beam_timer = 0.0
beam_boss = None
beam_reveal = 0.0
beam_capture_y = 0.0  # y position of captured ship during pull-up


def start_beam(boss_enemy):
    global beam_phase, beam_timer, beam_boss, beam_reveal
    beam_phase = BEAM_PHASE_EXPAND
    beam_timer = 0.0
    beam_reveal = 0.0
    beam_boss = boss_enemy
    beam_boss.dive_path = None  # stop normal dive movement
    # Tractor beam runs solo — release any escorts back to formation
    for esc in beam_boss.escorts:
        if esc.alive:
            esc.in_formation = True
            esc.is_escort = False
            esc.dive_path = None
            esc.node.scale.x = 1.0
    beam_boss.escorts = []


def stop_beam():
    global beam_phase, beam_timer, beam_boss, beam_reveal
    beam_phase = BEAM_PHASE_INACTIVE
    beam_timer = 0.0
    beam_reveal = 0.0
    if beam_boss is not None and beam_boss.alive:
        beam_boss.in_formation = True
        beam_boss.dive_path = None
        beam_boss.node.scale.x = 1.0
    beam_boss = None


@micropython.native
def draw_beam_fan(fb, boss_x, boss_y, reveal):
    """Draw a fan-shaped tractor beam from boss down to player area.
    reveal: 0.0-1.0, how far the beam has extended (radially from boss).
    Drawn in screen coordinates."""
    # Convert camera to screen coords
    cx = int(boss_x + 64)
    cy = int(boss_y + 64) + 6  # start just below boss sprite

    # Beam extends down to near player (about 50px below boss)
    max_len = int(PLAYER_Y - boss_y)
    beam_len = int(max_len * reveal)

    if beam_len <= 0:
        return

    # Draw horizontal lines that widen as they go down (fan shape)
    for dy in range(beam_len):
        # Fan width grows linearly with distance
        half_w = 2 + (dy * 10) // max_len
        y = cy + dy
        if y < 0 or y >= 128:
            continue
        # Alternate colors for the striped look
        if dy % 3 == 0:
            col = BEAM_COL_1
        elif dy % 3 == 1:
            col = BEAM_COL_2
        else:
            col = BEAM_COL_3
        # Draw horizontal line
        x_start = max(0, cx - half_w)
        x_end = min(127, cx + half_w)
        if x_start <= x_end:
            fb.hline(x_start, y, x_end - x_start + 1, col)


def update_beam(dt, player_obj, formation_obj):
    """Update tractor beam phases. Returns 'caught' if player captured."""
    global beam_phase, beam_timer, beam_reveal, beam_capture_y

    if beam_phase == BEAM_PHASE_INACTIVE:
        return None

    if beam_boss is None or not beam_boss.alive:
        stop_beam()
        return None

    beam_timer += dt

    if beam_phase == BEAM_PHASE_EXPAND:
        # Beam grows radially from boss toward player (~1.5 seconds)
        beam_reveal = min(beam_timer / 1.5, 1.0)
        if beam_reveal >= 1.0:
            beam_phase = BEAM_PHASE_ACTIVE
            beam_timer = 0.0

    elif beam_phase == BEAM_PHASE_ACTIVE:
        # Beam fully extended — check for capture (~2 seconds)
        beam_reveal = 1.0
        if beam_timer >= 2.0:
            beam_phase = BEAM_PHASE_RETRACT
            beam_timer = 0.0
        elif player_obj.alive and not player_obj.is_invincible():
            bx = beam_boss.node.position.x
            by = beam_boss.node.position.y
            dx = abs(player_obj.position.x - bx)
            dy = player_obj.position.y - by
            max_len = PLAYER_Y - by
            if max_len > 0:
                fan_half_w = 2 + (dy * 10) // max_len
            else:
                fan_half_w = 12
            if dx < fan_half_w + 4 and dy > 0 and dy < max_len + 5:
                # Start capture animation — ship gets pulled up
                beam_phase = BEAM_PHASE_CAPTURE
                beam_timer = 0.0
                beam_capture_y = player_obj.position.y
                # Show captured ship node (red color — use row 1)
                captured_ship_node.opacity = 1.0
                captured_ship_node.position.x = beam_boss.node.position.x
                captured_ship_node.position.y = beam_capture_y
                # Hide the real player
                player_obj.alive = False
                player_obj.opacity = 0.0
                return 'caught'

    elif beam_phase == BEAM_PHASE_CAPTURE:
        # Captured ship rotates and gets pulled UP to boss (~1.5 seconds)
        t = min(beam_timer / 1.5, 1.0)
        boss_y = beam_boss.node.position.y
        # Ship moves from player level up to ABOVE boss
        target_y = boss_y - 12  # held above the boss
        captured_ship_node.position.y = beam_capture_y + (target_y - beam_capture_y) * t
        captured_ship_node.position.x = beam_boss.node.position.x
        # Rotate as it goes up
        captured_ship_node.rotation = t * 6.28 * 2  # two full rotations

        if t >= 1.0:
            # Ship is now held by boss
            captured_ship_node.rotation = 0
            capture_player_ship(beam_boss)
            beam_phase = BEAM_PHASE_RETURN
            beam_timer = 0.0
            beam_reveal = 0.0

    elif beam_phase == BEAM_PHASE_RETRACT:
        # No capture — beam shrinks back (~0.5 seconds)
        beam_reveal = max(0, 1.0 - beam_timer / 0.5)
        if beam_reveal <= 0:
            beam_phase = BEAM_PHASE_RETURN
            beam_timer = 0.0

    elif beam_phase == BEAM_PHASE_RETURN:
        # Boss flies OFF SCREEN upward (~1.5 seconds), then respawns in formation
        t = min(beam_timer / 1.5, 1.0)
        # Fly upward off screen
        beam_boss.node.position.y -= 80 * dt
        # Move captured ship with boss (held above)
        if capturing_boss is beam_boss:
            captured_ship_node.position.x = beam_boss.node.position.x
            captured_ship_node.position.y = beam_boss.node.position.y - 12

        if beam_boss.node.position.y < -70:
            # Off screen — snap back to formation
            sx, sy = formation_obj.get_slot_screen_pos(
                beam_boss.slot_col, beam_boss.slot_row)
            beam_boss.node.position.x = sx
            beam_boss.node.position.y = sy
            beam_boss.in_formation = True
            # Captured ship stays with boss in formation
            if capturing_boss is beam_boss:
                captured_ship_node.position.x = sx
                captured_ship_node.position.y = sy - 12
            stop_beam()

    return None


# ── Initialize game systems ────────────────────────────────
formation = Formation()
bullets = BulletManager()
# Load bullet sprite texture
try:
    _bullet_tex = TextureResource("assets/bullets.bmp")
    bullets.set_texture(_bullet_tex)
except:
    pass
stars = Starfield(18)
explosions = ExplosionManager(explosion_nodes)
hud = HUD()
level = LevelData()
transforms = TransformManager()
popups = ScorePopups()

# Extra life tracking
EXTRA_LIFE_FIRST = const(20000)
EXTRA_LIFE_INTERVAL = const(70000)
next_extra_life = EXTRA_LIFE_FIRST

# Remove logo after loading
if _logo_node:
    _logo_node.mark_destroy()
    _logo_node = None
gc.collect()

# ── Idle animation timer ───────────────────────────────────
_idle_timer = 0.0
_idle_frame = False  # toggles between IDLE_FRAME_A and IDLE_FRAME_B


@micropython.native
def update_enemy_frames(formation, dt):
    """Update sprite frames: idle animation for formation, direction for divers."""
    global _idle_timer, _idle_frame
    _idle_timer += dt
    if _idle_timer >= 1.0 / IDLE_ANIM_FPS:
        _idle_timer -= 1.0 / IDLE_ANIM_FPS
        _idle_frame = not _idle_frame

    for e in formation.enemies:
        if e is None or not e.alive:
            continue
        if e.hit_flash > 0:
            continue  # don't change frame while showing dying palette

        # Get per-type idle frames
        ia, ib = get_idle_frames(e._orig_type)
        idle_fx = ib if _idle_frame else ia
        max_frame = ENEMY_FRAME_COUNT[e._orig_type] if e._orig_type < len(ENEMY_FRAME_COUNT) else 8

        if e.in_formation:
            e.node.frame_current_x = idle_fx
            e.node.scale.x = 1.0
        elif e.node.opacity > 0:
            nx = e.node.position.x
            last = e._last_x if hasattr(e, '_last_x') else nx
            dx = nx - last
            e._last_x = nx

            adx = abs(dx)
            if adx > 2:
                frame = 0
            elif adx > 0.8:
                frame = min(2, max_frame - 1)
            elif adx > 0.3:
                frame = min(4, max_frame - 1)
            else:
                frame = idle_fx

            if dx < -0.3:
                e.node.scale.x = -1.0
            elif dx > 0.3:
                e.node.scale.x = 1.0

            e.node.frame_current_x = min(frame, max_frame - 1)


# ── Game state ──────────────────────────────────────────────
state = ST_TITLE
state_timer = 0.0
entry_state = None
challenge_state = ChallengeState()


# ── Helper functions ────────────────────────────────────────
def play_sfx(sfx, channel):
    if sfx:
        engine_audio.play(sfx, channel, False)


def get_explode_sfx(etype):
    """Get the correct death sound for an enemy type."""
    if etype == ENEMY_BOSS or etype == ENEMY_BOSS_HIT:
        return explode_boss_sfx
    elif etype == ENEMY_BUTTERFLY:
        return explode_butterfly_sfx
    elif etype == ENEMY_BEE:
        return explode_bee_sfx
    elif etype >= ENEMY_SCORPION:
        return explode_boss_sfx  # transforms use boss kill sound
    return explode_bee_sfx


def check_extra_life():
    """Award extra life at score thresholds."""
    global next_extra_life
    if hud.score >= next_extra_life:
        hud.lives += 1
        play_sfx(extra_life_sfx, CH_MUSIC)
        if next_extra_life == EXTRA_LIFE_FIRST:
            next_extra_life = EXTRA_LIFE_FIRST + EXTRA_LIFE_INTERVAL
        else:
            next_extra_life += EXTRA_LIFE_INTERVAL


def start_stage():
    """Set up enemies for the current stage."""
    formation.reset()
    bullets.clear_all()
    stop_beam()
    transforms.reset()

    for row in range(FORM_ROWS):
        if row == 0:
            etype = ENEMY_BOSS
        elif row <= 2:
            etype = ENEMY_BUTTERFLY
        else:
            etype = ENEMY_BEE

        for col in range(FORM_COLS):
            if row == 0 and (col < 2 or col > 5):
                continue

            idx = row * FORM_COLS + col
            e = Enemy()
            e.init_for_stage(etype, col, row, enemy_nodes[idx])
            formation.set_enemy(col, row, e)

    formation.count_alive()
    level.set_stage(hud.stage)
    formation.dive_timer = level.dive_interval

    # If hostile fighter carried from previous stage, attach to a boss
    if hostile_fighter_carry:
        attach_hostile_to_boss(formation)


def hide_all_enemies():
    """Hide all enemy nodes."""
    for node in enemy_nodes:
        node.opacity = 0.0
        node.position.x = -200
        node.position.y = -200


def reset_game():
    """Reset for new game."""
    global next_extra_life
    hud.reset()
    hide_all_enemies()
    player.reset()
    wingman_node.opacity = 0.0
    bullets.clear_all()
    transforms.reset()
    stop_beam()
    release_captured_ship()
    kill_hostile_fighter()
    next_extra_life = EXTRA_LIFE_FIRST


def handle_player_fire():
    """Handle player firing — shared across all gameplay states."""
    if engine_io.A.is_just_pressed and player.alive:
        fired = False
        if player.dual_fighter:
            fired = bullets.fire_player(player.position.x, player.position.y)
            bullets.fire_player(player.position.x + WINGMAN_OFFSET_X, player.position.y)
        else:
            fired = bullets.fire_player(player.position.x, player.position.y)
        if fired:
            play_sfx(shoot_sfx, CH_SHOOT)


@micropython.native
def maybe_enemy_fire(enemy, bullets_mgr, level_data, player_x=0.0):
    """Check if a diving enemy should fire."""
    if random.random() < level_data.enemy_fire_chance:
        active_count = 0
        for i in range(MAX_ENEMY_BULLETS):
            if bullets_mgr.e_active[i]:
                active_count += 1
        if active_count < level_data.max_enemy_bullets:
            bullets_mgr.fire_enemy(enemy.node.position.x,
                                    enemy.node.position.y, player_x)
            play_sfx(enemy_shot_sfx, CH_EXPLODE)


# ── Main loop ──────────────────────────────────────────────
_last_ms = time.ticks_ms()
while True:
    if engine.tick():
        _now_ms = time.ticks_ms()
        dt = time.ticks_diff(_now_ms, _last_ms) * 0.001
        _last_ms = _now_ms
        if dt > 0.05:
            dt = 0.05  # cap delta time to prevent physics jumps

        # Always update stars
        stars.update(dt)

        # Get framebuffer for direct drawing
        fb_data = engine_draw.back_fb_data()
        fb = engine_draw.back_fb()

        # Draw stars (behind everything)
        stars.draw(fb_data)

        # ────────────────────────────────────────────────────
        # STATE: TITLE
        # ────────────────────────────────────────────────────
        if state == ST_TITLE:
            hud.draw_title(fb)

            if engine_io.A.is_just_pressed:
                reset_game()
                state = ST_STAGE_INTRO
                state_timer = 1.5
                play_sfx(level_start_sfx, CH_MUSIC)

        # ────────────────────────────────────────────────────
        # STATE: STAGE INTRO
        # ────────────────────────────────────────────────────
        elif state == ST_STAGE_INTRO:
            hud.set_stage(hud.stage)
            level.set_stage(hud.stage)

            # Show "STAGE X" or "CHALLENGE" text
            if level.is_challenge_stage():
                hud.draw_centered_text("CHALLENGE", 55)
            else:
                hud.draw_centered_text("STAGE " + str(hud.stage), 55)

            state_timer -= dt
            if state_timer <= 0:
                if level.is_challenge_stage():
                    # Challenge stage: enemies fly through, no formation
                    hide_all_enemies()
                    challenge_state.init(enemy_nodes)
                    bullets.clear_all()
                    state = ST_CHALLENGE
                else:
                    start_stage()
                    entry_state = EntryState(get_entry_pattern(hud.stage))
                    state = ST_ENTRY

        # ────────────────────────────────────────────────────
        # STATE: ENTRY (enemies flying in)
        # ────────────────────────────────────────────────────
        elif state == ST_ENTRY:
            formation.update(dt)
            update_enemy_frames(formation, dt)

            if update_entry(entry_state, formation, dt, level.entry_speed):
                state = ST_PLAYING
                formation.dive_timer = level.dive_interval

            # Player can shoot during entry
            player.update(dt, engine_io.LEFT.is_pressed,
                         engine_io.RIGHT.is_pressed)

            handle_player_fire()

            bullets.update(dt)

            # Check player bullets vs enemies already in formation
            hits = check_player_bullets_vs_enemies(bullets, formation)
            for bi, e in hits:
                bullets.p_active[bi] = False
                e.hp -= 1
                if e.hp <= 0:
                    e.start_dying()
                    explosions.spawn(e.node.position.x, e.node.position.y)
                    play_sfx(get_explode_sfx(e.type), CH_EXPLODE)
                    pts = POINTS[min(e.type, len(POINTS)-1)][0]
                    hud.add_score(pts)
                    # kill deferred — start_dying() handles it after flash
                    formation.count_alive()

            bullets.draw(fb)
            explosions.update(dt)
            hud.draw(fb)

        # ────────────────────────────────────────────────────
        # STATE: PLAYING (main gameplay)
        # ────────────────────────────────────────────────────
        elif state == ST_PLAYING:
            # Player input
            player.update(dt, engine_io.LEFT.is_pressed,
                         engine_io.RIGHT.is_pressed)

            # Wingman follows player
            if player.dual_fighter:
                wingman_node.position.x = player.position.x + WINGMAN_OFFSET_X
                wingman_node.position.y = player.position.y

            handle_player_fire()

            # Formation movement
            formation.update(dt)
            update_enemy_frames(formation, dt)

            # Update captured ship position (follows its boss)
            if capturing_boss is not None and capturing_boss.alive:
                captured_ship_node.position.x = capturing_boss.node.position.x
                captured_ship_node.position.y = capturing_boss.node.position.y - 12

            # Trigger dive attacks
            diver = maybe_trigger_dive(formation, level, dt)
            if diver is not None:
                play_sfx(dive_sfx, CH_SHOOT)  # reuse channel for dive swoosh

            # Update diving enemies
            for e in formation.enemies:
                if e is not None and e.alive and not e.in_formation and e.entry_done:
                    if e is beam_boss:
                        continue  # beam boss is controlled by beam system
                    done = update_diving_enemy(e, dt, level.dive_speed, formation)
                    if not done:
                        is_boss = e.type == ENEMY_BOSS or e.type == ENEMY_BOSS_HIT
                        if is_boss and beam_phase == BEAM_PHASE_INACTIVE \
                           and e.node.position.y > 10 and e.node.position.y < 30 \
                           and random.random() < 0.12:
                            # Boss stops mid-dive to fire tractor beam
                            start_beam(e)
                            play_sfx(beam_sfx, CH_MUSIC)
                        elif not is_boss:
                            # Only non-boss enemies fire bullets
                            maybe_enemy_fire(e, bullets, level, player.position.x)

            # Update tractor beam
            if beam_phase != BEAM_PHASE_INACTIVE:
                result = update_beam(dt, player, formation)
                if result == 'caught':
                    play_sfx(capture_sfx, CH_PLAYER_DIE)
                    # Player caught — enter dying state (capture animation runs in beam)
                    state = ST_DYING
                    state_timer = 2.5  # longer to allow capture animation

            # Update bullets
            bullets.update(dt)

            # ── Collision detection ──
            # Player bullets vs enemies
            hits = check_player_bullets_vs_enemies(bullets, formation)
            for bi, e in hits:
                bullets.p_active[bi] = False
                e.hp -= 1
                if e.hp <= 0:
                    diving = not e.in_formation
                    # Flash dying palette then explode
                    e.start_dying()
                    explosions.spawn(e.node.position.x, e.node.position.y)
                    play_sfx(get_explode_sfx(e.type), CH_EXPLODE)
                    # Boss convoy scoring
                    is_boss = e.type == ENEMY_BOSS or e.type == ENEMY_BOSS_HIT
                    if is_boss and diving and len(e.escorts) > 0:
                        pts = 800 if len(e.escorts) == 1 else 1600
                        popups.spawn(pts, e.node.position.x, e.node.position.y)
                    elif is_boss and diving:
                        pts = 400
                        popups.spawn(pts, e.node.position.x, e.node.position.y)
                    else:
                        pts = POINTS[min(e.type, len(POINTS)-1)][1 if diving else 0]
                    hud.add_score(pts)
                    if is_boss and capturing_boss is e and diving:
                        start_rescue()
                        engine_audio.stop(CH_PLAYER_DIE)  # stop capture sound
                        engine_audio.stop(CH_MUSIC)
                        play_sfx(rescue_sfx, CH_MUSIC)
                    elif is_boss and capturing_boss is e and not diving:
                        # Boss killed in formation — captured ship becomes hostile enemy
                        hx = captured_ship_node.position.x
                        hy = captured_ship_node.position.y
                        capturing_boss = None
                        activate_hostile_fighter(hx, hy)
                    # kill deferred — start_dying() handles it after flash
                    formation.count_alive()
                else:
                    # Boss hit but not dead — switch to hit sprite
                    if e.type == ENEMY_BOSS:
                        e.node.frame_current_y = ENEMY_BOSS_HIT
                        e.type = ENEMY_BOSS_HIT
                        play_sfx(explode_boss_hit_sfx, CH_EXPLODE)

            # Enemy bullets vs player
            hit_idx = check_enemy_bullets_vs_player(bullets, player)
            if hit_idx >= 0:
                bullets.e_active[hit_idx] = False
                state = ST_DYING
                state_timer = 1.5
                player.alive = False
                player.opacity = 0.0
                wingman_node.opacity = 0.0
                player_exp_node.position.x = player.position.x
                player_exp_node.position.y = player.position.y
                player_exp_node.opacity = 1.0
                player_exp_node.frame_current_x = 0
                player_exp_node.playing = True
                play_sfx(die_sfx, CH_PLAYER_DIE)
                stop_beam()

            # Diving enemies body-to-body with player
            if state == ST_PLAYING:  # not already dying
                diver_hit = check_divers_vs_player(formation, player)
                if diver_hit is not None:
                    explosions.spawn(diver_hit.node.position.x,
                                    diver_hit.node.position.y)
                    diver_hit.kill()
                    formation.count_alive()
                    state = ST_DYING
                    state_timer = 1.5
                    player.alive = False
                    player.opacity = 0.0
                    player_exp_node.position.x = player.position.x
                    player_exp_node.position.y = player.position.y
                    player_exp_node.opacity = 1.0
                    play_sfx(die_sfx, CH_PLAYER_DIE)
                    stop_beam()

            # Transform enemies — bee morphs into group of 3
            morphed = transforms.try_morph(formation, hud.stage,
                                           enemy_nodes, dt)
            if morphed:
                play_sfx(transform_sfx, CH_EXPLODE)

            # Update transform groups (they fly through and exit)
            transforms.update(dt, lambda x, y: bullets.fire_enemy(x, y, player.position.x))

            # Check player bullets vs transform enemies
            if state == ST_PLAYING:
                for bi in range(MAX_PLAYER_BULLETS):
                    if not bullets.p_active[bi]:
                        continue
                    hit = transforms.check_bullet_hit(
                        bullets.p_x[bi], bullets.p_y[bi])
                    if hit:
                        g, idx = hit
                        bullets.p_active[bi] = False
                        ex = g.enemies[idx][0].position.x
                        ey = g.enemies[idx][0].position.y
                        transforms.kill_enemy(g, idx)
                        explosions.spawn(ex, ey)
                        play_sfx(explode_boss_sfx, CH_EXPLODE)  # transforms use boss kill sound
                        hud.add_score(TRANSFORM_INDIVIDUAL_PTS)
                        # Bonus if all 3 killed
                        if g.kills >= 3:
                            hud.add_score(g.bonus)
                            popups.spawn(g.bonus, ex, ey)

            # Transform enemies body-to-body with player
            if state == ST_PLAYING and player.alive and not player.is_invincible():
                t_hit = transforms.check_player_collision(
                    player.position.x, player.position.y)
                if t_hit:
                    g, idx = t_hit
                    ex = g.enemies[idx][0].position.x
                    ey = g.enemies[idx][0].position.y
                    transforms.kill_enemy(g, idx)
                    explosions.spawn(ex, ey)
                    state = ST_DYING
                    state_timer = 1.5
                    player.alive = False
                    player.opacity = 0.0
                    player_exp_node.position.x = player.position.x
                    player_exp_node.position.y = player.position.y
                    player_exp_node.opacity = 1.0
                    player_exp_node.frame_current_x = 0
                    player_exp_node.playing = True
                    play_sfx(die_sfx, CH_PLAYER_DIE)
                    stop_beam()

            # Hostile captured fighter
            if hostile_fighter_active and hostile_fighter_alive:
                update_hostile_fighter(dt, bullets, player.position.x)

                # Check player bullets vs hostile fighter
                if hostile_fighter_active:
                    for bi in range(MAX_PLAYER_BULLETS):
                        if not bullets.p_active[bi]:
                            continue
                        dx = abs(bullets.p_x[bi] - hostile_fighter_x)
                        dy = abs(bullets.p_y[bi] - hostile_fighter_y)
                        if dx < PLAYER_HALF_W and dy < PLAYER_HALF_H:
                            bullets.p_active[bi] = False
                            explosions.spawn(hostile_fighter_x, hostile_fighter_y)
                            play_sfx(explode_boss_sfx, CH_EXPLODE)
                            hud.add_score(HOSTILE_FIGHTER_POINTS)
                            popups.spawn(HOSTILE_FIGHTER_POINTS, hostile_fighter_x, hostile_fighter_y)
                            kill_hostile_fighter()
                            break

                # Check hostile fighter body vs player
                if hostile_fighter_active and player.alive and not player.is_invincible():
                    dx = abs(player.position.x - hostile_fighter_x)
                    dy = abs(player.position.y - hostile_fighter_y)
                    if dx < PLAYER_HALF_W + 4 and dy < PLAYER_HALF_H + 4:
                        explosions.spawn(hostile_fighter_x, hostile_fighter_y)
                        kill_hostile_fighter()
                        state = ST_DYING
                        state_timer = 1.5
                        player.alive = False
                        player.opacity = 0.0
                        wingman_node.opacity = 0.0
                        player_exp_node.position.x = player.position.x
                        player_exp_node.position.y = player.position.y
                        player_exp_node.opacity = 1.0
                        player_exp_node.frame_current_x = 0
                        player_exp_node.playing = True
                        play_sfx(die_sfx, CH_PLAYER_DIE)
                        stop_beam()

            # Extra life check
            check_extra_life()

            # Check stage clear (no formation enemies AND no active transforms)
            if formation.alive_count <= 0 and len(transforms.groups) == 0:
                state = ST_STAGE_CLEAR
                state_timer = 1.5
                stop_beam()
                bullets.clear_all()

            # Draw
            bullets.draw(fb)
            if beam_phase != BEAM_PHASE_INACTIVE and beam_boss is not None:
                draw_beam_fan(fb, beam_boss.node.position.x,
                             beam_boss.node.position.y, beam_reveal)
            explosions.update(dt)
            hud.draw(fb)

        # ────────────────────────────────────────────────────
        # STATE: CHALLENGE (bonus round — 5 waves of 8)
        # ────────────────────────────────────────────────────
        elif state == ST_CHALLENGE:
            player.update(dt, engine_io.LEFT.is_pressed,
                         engine_io.RIGHT.is_pressed)

            handle_player_fire()

            # Update challenge wave enemies (fly-through patterns)
            done = update_challenge(challenge_state, dt)
            if done:
                state = ST_STAGE_CLEAR
                state_timer = 3.0  # longer to show results
                if challenge_state.kills >= CHALLENGE_TOTAL:
                    hud.add_score(CHALLENGE_PERFECT_BONUS)
                    play_sfx(challenge_perfect_sfx, CH_MUSIC)
                    popups.spawn("PERFECT!", 0, -10)
                    popups.spawn(CHALLENGE_PERFECT_BONUS, 0, 0)
                else:
                    play_sfx(challenge_over_sfx, CH_MUSIC)
                # Show hit results
                popups.spawn("HITS:" + str(challenge_state.kills), 0, 10)

            bullets.update(dt)

            # Check bullets vs challenge enemies
            for bi in range(MAX_PLAYER_BULLETS):
                if not bullets.p_active[bi]:
                    continue
                bx = bullets.p_x[bi]
                by = bullets.p_y[bi]
                for ce in challenge_state.enemies:
                    if not ce.active or not ce.alive:
                        continue
                    ex = ce.node.position.x
                    ey = ce.node.position.y
                    if abs(bx - ex) < ENEMY_HALF + 1 and abs(by - ey) < ENEMY_HALF + 2:
                        bullets.p_active[bi] = False
                        ce.alive = False
                        ce.active = False
                        ce.node.opacity = 0.0
                        explosions.spawn(ex, ey)
                        play_sfx(explode_bee_sfx, CH_EXPLODE)
                        challenge_state.kills += 1
                        challenge_state.wave_kills[ce.wave_idx] += 1
                        hud.add_score(CHALLENGE_HIT_POINTS)
                        # Check if entire wave of 8 is cleared
                        if challenge_state.wave_kills[ce.wave_idx] >= CHALLENGE_ENEMIES_PER_WAVE \
                           and not challenge_state.wave_done[ce.wave_idx]:
                            challenge_state.wave_done[ce.wave_idx] = True
                            # Bonus depends on which challenge stage this is
                            # Challenges at stages 3,7,11,15,19,23,27...
                            challenge_num = (hud.stage - 3) // 4 + 1
                            if challenge_num <= 2:
                                wave_bonus = 1000
                            elif challenge_num <= 4:
                                wave_bonus = 1500
                            elif challenge_num <= 6:
                                wave_bonus = 2000
                            else:
                                wave_bonus = 3000
                            hud.add_score(wave_bonus)
                            popups.spawn(wave_bonus, ex, ey)
                        break

            bullets.draw(fb)
            explosions.update(dt)
            hud.draw(fb)

            # Show kills counter
            # Per-wave bonus popups handled by challenge update

        # ────────────────────────────────────────────────────
        # STATE: DYING (player death animation)
        # ────────────────────────────────────────────────────
        elif state == ST_DYING:
            state_timer -= dt
            formation.update(dt)
            update_enemy_frames(formation, dt)
            bullets.update(dt)
            explosions.update(dt)

            # Continue beam animation (capture pull-up and return)
            if beam_phase != BEAM_PHASE_INACTIVE:
                update_beam(dt, player, formation)

            # Update captured ship position (follows boss)
            if capturing_boss is not None and capturing_boss.alive:
                captured_ship_node.position.x = capturing_boss.node.position.x
                captured_ship_node.position.y = capturing_boss.node.position.y - 12

            # Player explosion fades (only if not a beam capture)
            if player_exp_node.opacity > 0:
                player_exp_node.opacity = max(0, state_timer / 1.5)
                if state_timer <= 0.5:
                    player_exp_node.opacity = 0.0

            # Draw
            bullets.draw(fb)
            if beam_phase != BEAM_PHASE_INACTIVE and beam_boss is not None:
                draw_beam_fan(fb, beam_boss.node.position.x,
                             beam_boss.node.position.y, beam_reveal)
            hud.draw(fb)

            # Show "FIGHTER CAPTURED" during capture phase
            if beam_phase == BEAM_PHASE_CAPTURE or \
               (beam_phase == BEAM_PHASE_RETURN and capturing_boss is not None):
                hud.draw_centered_text("FIGHTER CAPTURED", 55)

            if state_timer <= 0:
                player_exp_node.opacity = 0.0
                hud.lives -= 1
                if hud.lives <= 0:
                    state = ST_GAME_OVER
                    state_timer = 1.0
                    hide_all_enemies()
                    bullets.clear_all()
                    stop_beam()
                    release_captured_ship()
                else:
                    player.reset()
                    bullets.clear_all()
                    # Return all diving enemies to formation
                    for e in formation.enemies:
                        if e is not None and e.alive and not e.in_formation \
                           and e is not beam_boss:
                            e.in_formation = True
                            e.dive_path = None
                            e.escorts = []
                            sx, sy = formation.get_slot_screen_pos(
                                e.slot_col, e.slot_row)
                            e.node.position.x = sx
                            e.node.position.y = sy
                    state = ST_PLAYING

        # ────────────────────────────────────────────────────
        # STATE: STAGE CLEAR
        # ────────────────────────────────────────────────────
        elif state == ST_STAGE_CLEAR:
            state_timer -= dt
            explosions.update(dt)
            hud.draw(fb)

            if state_timer <= 0:
                hide_all_enemies()
                hud.stage += 1
                state = ST_STAGE_INTRO
                state_timer = 1.5
                play_sfx(level_start_sfx, CH_MUSIC)

        # ────────────────────────────────────────────────────
        # STATE: GAME OVER
        # ────────────────────────────────────────────────────
        elif state == ST_GAME_OVER:
            state_timer -= dt
            if state_timer <= 0:
                state_timer = 0
            hud.draw(fb)
            hud.draw_game_over(fb)

            if state_timer <= 0 and engine_io.A.is_just_pressed:
                hide_all_enemies()
                state = ST_TITLE

        # ── Update hostile fighter entry (flying in from previous stage) ──
        if hostile_fighter_entry_target_boss is not None:
            update_hostile_entry(dt, formation)

        # ── Update dying enemy flash timers ──
        _any_died = False
        for e in formation.enemies:
            if e is not None and e.hit_flash > 0:
                if e.update_flash(dt):
                    _any_died = True
        if _any_died:
            formation.count_alive()

        # ── Always draw popups ──
        popups.update_and_draw(dt)

        # ── Always update rescue animation and wingman position ──
        if rescue_active:
            update_rescue(dt)
        if player.dual_fighter and player.alive and player.opacity > 0:
            wingman_node.position.x = player.position.x + WINGMAN_OFFSET_X
            wingman_node.position.y = player.position.y
            wingman_node.opacity = player.opacity  # match player (blink together)
        elif not player.alive or not player.dual_fighter:
            wingman_node.opacity = 0.0

        # ── Per-frame cleanup ──
        gc.collect()
