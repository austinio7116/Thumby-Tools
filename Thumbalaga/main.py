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
from dive import update_diving_enemy, maybe_trigger_dive
from entry_patterns import EntryState, get_entry_pattern, update_entry
from collision import (check_player_bullets_vs_enemies,
                       check_enemy_bullets_vs_player,
                       check_divers_vs_player)
from level import LevelData
from challenge import ChallengeState, update_challenge, CHALLENGE_HIT_POINTS, CHALLENGE_PERFECT_BONUS, CHALLENGE_TOTAL

# ── Setup ───────────────────────────────────────────────────
engine.fps_limit(60)

camera = CameraNode()  # Default position (0, 0, 0) — sprites use -64 to +64
engine_draw.set_background_color(Color(COL_BLACK))


# ── Load resources ──────────────────────────────────────────
def load_tex(path):
    engine.tick()
    return TextureResource(path)


player_tex = load_tex("assets/player.bmp")
enemy_tex = load_tex("assets/enemies.bmp")
explosion_tex = load_tex("assets/explosion.bmp")
player_exp_tex = load_tex("assets/player_explosion.bmp")
beam_tex = load_tex("assets/tractor_beam.bmp")

# Try to load sounds - use None if not available
shoot_sfx = None
explode_sfx = None
die_sfx = None
try:
    shoot_sfx = WaveSoundResource("assets/shoot.wav")
except:
    pass
try:
    explode_sfx = WaveSoundResource("assets/explode.wav")
except:
    pass
try:
    die_sfx = WaveSoundResource("assets/player_die.wav")
except:
    pass


# ── Create player ───────────────────────────────────────────
player = Player(player_tex)
camera.add_child(player)


# ── Create enemy node pool ──────────────────────────────────
enemy_nodes = []
transparent = Color(COL_MAGENTA)
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
player_exp_node.frame_count_x = EXPLOSION_FRAMES
player_exp_node.frame_count_y = 1
player_exp_node.fps = EXPLOSION_FPS
player_exp_node.playing = False
player_exp_node.loop = False
player_exp_node.opacity = 0.0
player_exp_node.layer = 16
camera.add_child(player_exp_node)

# Tractor beam node
beam_node = Sprite2DNode()
beam_node.texture = beam_tex
beam_node.transparent_color = transparent
beam_node.frame_count_x = 3   # 3 animation frames
beam_node.frame_count_y = 1
beam_node.fps = BEAM_FPS
beam_node.playing = False
beam_node.loop = True
beam_node.opacity = 0.0
beam_node.layer = 4  # behind enemies
camera.add_child(beam_node)

# Beam state machine
# Phase 0: inactive
# Phase 1: boss diving down to hover position
# Phase 2: hovering, beam expanding
# Phase 3: beam active (checking for capture)
# Phase 4: beam retracting, boss returning to formation
BEAM_PHASE_INACTIVE = const(0)
BEAM_PHASE_DIVE = const(1)
BEAM_PHASE_EXPAND = const(2)
BEAM_PHASE_ACTIVE = const(3)
BEAM_PHASE_RETRACT = const(4)

beam_phase = BEAM_PHASE_INACTIVE
beam_timer = 0.0
beam_boss = None
beam_hover_y = 30.0  # where the boss stops to hover (camera coords)
beam_start_x = 0.0
beam_start_y = 0.0


def start_beam(boss_enemy):
    global beam_phase, beam_timer, beam_boss, beam_start_x, beam_start_y
    # Boss is already mid-dive — stop it here and start the beam
    beam_phase = BEAM_PHASE_EXPAND
    beam_timer = 0.0
    beam_boss = boss_enemy
    beam_boss.dive_path = None  # stop normal dive movement
    beam_start_x = boss_enemy.node.position.x
    beam_start_y = boss_enemy.node.position.y


def stop_beam():
    global beam_phase, beam_timer, beam_boss
    beam_phase = BEAM_PHASE_INACTIVE
    beam_timer = 0.0
    beam_node.opacity = 0.0
    beam_node.playing = False
    if beam_boss is not None and beam_boss.alive:
        # Return boss to formation
        beam_boss.in_formation = True
        beam_boss.dive_path = None
        beam_boss.node.scale.x = 1.0
    beam_boss = None


def update_beam(dt, player_obj, formation_obj):
    """Update tractor beam phases. Returns True if player caught."""
    global beam_phase, beam_timer

    if beam_phase == BEAM_PHASE_INACTIVE:
        return False

    if beam_boss is None or not beam_boss.alive:
        stop_beam()
        return False

    beam_timer += dt
    boss_node = beam_boss.node

    if beam_phase == BEAM_PHASE_EXPAND:
        # Beam revealed radially — full size sprite, no stretching
        # Slide beam down from boss to reveal it gradually (~1.5 seconds)
        t = min(beam_timer / 1.5, 1.0)
        beam_node.position.x = boss_node.position.x
        # Start with beam centered on boss (hidden behind it), slide down
        beam_node.position.y = boss_node.position.y + 4 + t * 14
        beam_node.opacity = t
        beam_node.playing = True
        beam_node.scale.x = 1.0  # never stretch
        beam_node.scale.y = 1.0

        if t >= 1.0:
            beam_phase = BEAM_PHASE_ACTIVE
            beam_timer = 0.0
            beam_node.opacity = 1.0

    elif beam_phase == BEAM_PHASE_ACTIVE:
        # Beam fully active — check for player capture (~2 seconds)
        beam_node.position.x = boss_node.position.x
        beam_node.position.y = boss_node.position.y + 18

        if beam_timer >= 2.0:
            beam_phase = BEAM_PHASE_RETRACT
            beam_timer = 0.0
        elif player_obj.alive and not player_obj.is_invincible():
            dx = abs(player_obj.position.x - boss_node.position.x)
            dy = player_obj.position.y - boss_node.position.y
            if dx < 12 and dy > 0 and dy < 35:
                stop_beam()
                return True  # caught!

    elif beam_phase == BEAM_PHASE_RETRACT:
        # Beam fades out (~0.4 seconds), no stretching
        t = min(beam_timer / 0.4, 1.0)
        beam_node.opacity = 1.0 - t

        if t >= 1.0:
            beam_node.opacity = 0.0
            beam_node.playing = False
            # Boss flies back up to formation
            beam_timer = 0.0
            # Snap back to formation slot
            sx, sy = formation_obj.get_slot_screen_pos(
                beam_boss.slot_col, beam_boss.slot_row)
            boss_node.position.x = sx
            boss_node.position.y = sy
            stop_beam()

    return False


# ── Initialize game systems ────────────────────────────────
formation = Formation()
bullets = BulletManager()
stars = Starfield(18)
explosions = ExplosionManager(explosion_nodes)
hud = HUD()
level = LevelData()

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

    idle_fx = IDLE_FRAME_B if _idle_frame else IDLE_FRAME_A

    for e in formation.enemies:
        if e is None or not e.alive:
            continue
        if e.in_formation:
            # Idle: alternate between two facing-down frames
            e.node.frame_current_x = idle_fx
            e.node.scale.x = 1.0
        elif e.node.opacity > 0:
            # Moving (entry or dive): pick frame from velocity
            nx = e.node.position.x
            last = e._last_x if hasattr(e, '_last_x') else nx
            dx = nx - last
            e._last_x = nx

            adx = abs(dx)
            if adx > 2:
                frame = 0      # facing sideways
            elif adx > 0.8:
                frame = 2      # angled
            elif adx > 0.3:
                frame = 4      # mostly down
            else:
                frame = idle_fx  # straight down

            # Mirror horizontally for leftward movement
            # (frame 0 faces right by default, mirror for left)
            if dx < -0.3:
                e.node.scale.x = -1.0
            elif dx > 0.3:
                e.node.scale.x = 1.0

            e.node.frame_current_x = frame


# ── Game state ──────────────────────────────────────────────
state = ST_TITLE
state_timer = 0.0
entry_state = None
challenge_state = ChallengeState()


# ── Helper functions ────────────────────────────────────────
def play_sfx(sfx, channel):
    if sfx:
        engine_audio.play(sfx, channel, False)


def get_transform_type(stage):
    """Get which transform enemy type to use for this stage, or None."""
    result = None
    for min_stage, etype in TRANSFORM_STAGES:
        if stage >= min_stage:
            result = etype
    return result


def start_stage():
    """Set up enemies for the current stage."""
    formation.reset()
    bullets.clear_all()
    stop_beam()

    transform = get_transform_type(hud.stage)

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

            # Replace some bees with transform enemies in later stages
            actual_type = etype
            if transform is not None and etype == ENEMY_BEE:
                # Replace corner bees with transform enemies
                if (row == 4 and (col == 0 or col == 7)) or \
                   (row == 3 and (col == 0 or col == 7)):
                    actual_type = transform

            idx = row * FORM_COLS + col
            e = Enemy()
            e.init_for_stage(actual_type, col, row, enemy_nodes[idx])
            formation.set_enemy(col, row, e)

    formation.count_alive()
    level.set_stage(hud.stage)
    formation.dive_timer = level.dive_interval


def hide_all_enemies():
    """Hide all enemy nodes."""
    for node in enemy_nodes:
        node.opacity = 0.0
        node.position.x = -200
        node.position.y = -200


def reset_game():
    """Reset for new game."""
    hud.reset()
    hide_all_enemies()
    player.reset()
    bullets.clear_all()


@micropython.native
def maybe_enemy_fire(enemy, bullets_mgr, level_data):
    """Check if a diving enemy should fire."""
    if random.random() < level_data.enemy_fire_chance:
        active_count = 0
        for i in range(MAX_ENEMY_BULLETS):
            if bullets_mgr.e_active[i]:
                active_count += 1
        if active_count < level_data.max_enemy_bullets:
            bullets_mgr.fire_enemy(enemy.node.position.x,
                                    enemy.node.position.y)


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

            if engine_io.A.is_just_pressed:
                if bullets.fire_player(player.position.x, player.position.y):
                    play_sfx(shoot_sfx, CH_SHOOT)

            bullets.update(dt)

            # Check player bullets vs enemies already in formation
            hits = check_player_bullets_vs_enemies(bullets, formation)
            for bi, e in hits:
                bullets.p_active[bi] = False
                e.hp -= 1
                if e.hp <= 0:
                    explosions.spawn(e.node.position.x, e.node.position.y)
                    play_sfx(explode_sfx, CH_EXPLODE)
                    pts = POINTS[e.type][0]
                    hud.add_score(pts)
                    e.kill()
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

            if engine_io.A.is_just_pressed:
                if bullets.fire_player(player.position.x, player.position.y):
                    play_sfx(shoot_sfx, CH_SHOOT)

            # Formation movement
            formation.update(dt)
            update_enemy_frames(formation, dt)

            # Trigger dive attacks
            maybe_trigger_dive(formation, level, dt)

            # Update diving enemies
            for e in formation.enemies:
                if e is not None and e.alive and not e.in_formation and e.entry_done:
                    if e is beam_boss:
                        continue  # beam boss is controlled by beam system
                    done = update_diving_enemy(e, dt, level.dive_speed, formation)
                    if not done:
                        is_boss = e.type == ENEMY_BOSS or e.type == ENEMY_BOSS_HIT
                        if is_boss and beam_phase == BEAM_PHASE_INACTIVE \
                           and e.dive_t > 0.2 and e.dive_t < 0.5 \
                           and e.node.position.y < 15 \
                           and random.random() < 0.15:
                            # Boss stops mid-dive to fire tractor beam
                            start_beam(e)
                        elif not is_boss:
                            # Only non-boss enemies fire bullets
                            maybe_enemy_fire(e, bullets, level)

            # Update tractor beam
            if beam_phase != BEAM_PHASE_INACTIVE:
                caught = update_beam(dt, player, formation)
                if caught:
                    # Player caught by beam — lose a life
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
                    explosions.spawn(e.node.position.x, e.node.position.y)
                    play_sfx(explode_sfx, CH_EXPLODE)
                    pts = POINTS[e.type][1 if diving else 0]
                    hud.add_score(pts)
                    e.kill()
                    formation.count_alive()
                else:
                    # Boss hit but not dead — switch to hit sprite
                    if e.type == ENEMY_BOSS:
                        e.node.frame_current_y = ENEMY_BOSS_HIT

            # Enemy bullets vs player
            hit_idx = check_enemy_bullets_vs_player(bullets, player)
            if hit_idx >= 0:
                bullets.e_active[hit_idx] = False
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

            # Check stage clear
            if formation.alive_count <= 0:
                state = ST_STAGE_CLEAR
                state_timer = 1.5
                stop_beam()
                bullets.clear_all()

            # Draw
            bullets.draw(fb)
            explosions.update(dt)
            hud.draw(fb)

        # ────────────────────────────────────────────────────
        # STATE: CHALLENGE (bonus round — 5 waves of 8)
        # ────────────────────────────────────────────────────
        elif state == ST_CHALLENGE:
            player.update(dt, engine_io.LEFT.is_pressed,
                         engine_io.RIGHT.is_pressed)

            if engine_io.A.is_just_pressed:
                if bullets.fire_player(player.position.x, player.position.y):
                    play_sfx(shoot_sfx, CH_SHOOT)

            # Update challenge wave enemies (fly-through patterns)
            done = update_challenge(challenge_state, dt)
            if done:
                state = ST_STAGE_CLEAR
                state_timer = 2.0
                # Perfect bonus
                if challenge_state.kills >= CHALLENGE_TOTAL:
                    hud.add_score(CHALLENGE_PERFECT_BONUS)
                    hud.draw_centered_text("PERFECT!", 45)

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
                        play_sfx(explode_sfx, CH_EXPLODE)
                        challenge_state.kills += 1
                        hud.add_score(CHALLENGE_HIT_POINTS)
                        break

            bullets.draw(fb)
            explosions.update(dt)
            hud.draw(fb)

            # Show kills counter
            hud.draw_centered_text(str(challenge_state.kills) + "/" + str(CHALLENGE_TOTAL), 110)

        # ────────────────────────────────────────────────────
        # STATE: DYING (player death animation)
        # ────────────────────────────────────────────────────
        elif state == ST_DYING:
            state_timer -= dt
            formation.update(dt)
            update_enemy_frames(formation, dt)
            bullets.update(dt)
            explosions.update(dt)

            # Player explosion fades
            if player_exp_node.opacity > 0:
                player_exp_node.opacity = max(0, state_timer / 1.5)
                if state_timer <= 0.5:
                    player_exp_node.opacity = 0.0

            bullets.draw(fb)
            hud.draw(fb)

            if state_timer <= 0:
                player_exp_node.opacity = 0.0
                hud.lives -= 1
                if hud.lives <= 0:
                    state = ST_GAME_OVER
                    state_timer = 1.0
                    hide_all_enemies()
                    bullets.clear_all()
                    stop_beam()
                else:
                    player.reset()
                    bullets.clear_all()
                    # Return all diving enemies to formation
                    for e in formation.enemies:
                        if e is not None and e.alive and not e.in_formation:
                            e.in_formation = True
                            e.dive_path = None
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

        # ── Per-frame cleanup ──
        gc.collect()
