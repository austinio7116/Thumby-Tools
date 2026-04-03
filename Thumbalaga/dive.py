import random
from constants import *

# Dive paths: lists of (dx, dy) waypoints relative to start position.
# Enemy interpolates from waypoint to waypoint as t goes 0→1.

DIVE_CENTER = [
    (0, 0),
    (-10, 25),
    (10, 50),
    (-5, 75),
    (0, 100),
    (0, 140),
]

DIVE_SWEEP_LEFT = [
    (0, 0),
    (15, 15),
    (25, 35),
    (15, 60),
    (-10, 85),
    (-5, 110),
    (0, 140),
]

DIVE_SWEEP_RIGHT = [
    (0, 0),
    (-15, 15),
    (-25, 35),
    (-15, 60),
    (10, 85),
    (5, 110),
    (0, 140),
]

DIVE_LOOP = [
    (0, 0),
    (-20, 15),
    (-30, 0),
    (-20, -15),
    (0, 0),
    (10, 25),
    (5, 55),
    (0, 85),
    (0, 140),
]

DIVE_BOSS_SPECIAL = [
    (0, 0),
    (-20, 20),
    (-35, 45),
    (-20, 70),
    (20, 85),
    (35, 60),
    (20, 40),
    (0, 55),
    (-10, 80),
    (0, 110),
    (0, 140),
]

ALL_DIVE_PATHS = [DIVE_CENTER, DIVE_SWEEP_LEFT, DIVE_SWEEP_RIGHT, DIVE_LOOP]
BOSS_DIVE_PATHS = [DIVE_BOSS_SPECIAL, DIVE_LOOP]


def select_dive_path(enemy):
    if enemy.type == ENEMY_BOSS:
        return random.choice(BOSS_DIVE_PATHS)
    if enemy.slot_col < FORM_COLS // 2:
        return random.choice([DIVE_SWEEP_LEFT, DIVE_CENTER, DIVE_LOOP])
    else:
        return random.choice([DIVE_SWEEP_RIGHT, DIVE_CENTER, DIVE_LOOP])


def start_dive(enemy, formation=None):
    """Initiate a dive attack. Boss grabs nearby butterfly escorts if formation given."""
    enemy.in_formation = False
    enemy.dive_t = 0.0
    enemy.dive_start_x = enemy.node.position.x
    enemy.dive_start_y = enemy.node.position.y
    enemy.dive_path = select_dive_path(enemy)
    enemy.fire_timer = random.random() * 0.5 + 0.3
    enemy.escorts = []

    # Boss convoy: grab 1-2 butterflies from rows 1-2 as escorts
    if formation and (enemy.type == ENEMY_BOSS or enemy.type == ENEMY_BOSS_HIT):
        for row in [1, 2]:  # butterfly rows
            for dc in [0, -1, 1, -2, 2]:
                col = enemy.slot_col + dc
                if col < 0 or col >= FORM_COLS:
                    continue
                esc = formation.get_enemy(col, row)
                if esc and esc.alive and esc.in_formation and \
                   esc.type == ENEMY_BUTTERFLY and len(enemy.escorts) < 2:
                    esc.in_formation = False
                    esc.is_escort = True
                    esc.dive_path = enemy.dive_path
                    esc.dive_t = 0.0
                    esc.dive_start_x = esc.node.position.x
                    esc.dive_start_y = esc.node.position.y
                    enemy.escorts.append(esc)
            if len(enemy.escorts) >= 2:
                break


@micropython.native
def update_diving_enemy(enemy, dt, dive_speed, formation):
    """Advance enemy along dive path. Returns True when dive complete."""
    enemy.dive_t += dt * dive_speed

    path = enemy.dive_path
    seg_count = len(path) - 1

    if enemy.dive_t >= 1.0:
        # Dive complete — return to formation
        enemy.in_formation = True
        enemy.dive_t = 0.0
        enemy.dive_path = None
        enemy.node.scale.x = 1.0
        sx, sy = formation.get_slot_screen_pos(enemy.slot_col, enemy.slot_row)
        enemy.node.position.x = sx
        enemy.node.position.y = sy
        # Return escorts too
        for esc in enemy.escorts:
            if esc.alive:
                esc.in_formation = True
                esc.is_escort = False
                esc.dive_path = None
                esc.node.scale.x = 1.0
                esx, esy = formation.get_slot_screen_pos(esc.slot_col, esc.slot_row)
                esc.node.position.x = esx
                esc.node.position.y = esy
        enemy.escorts = []
        return True

    t_scaled = enemy.dive_t * seg_count
    seg_idx = int(t_scaled)
    seg_t = t_scaled - seg_idx

    if seg_idx >= seg_count:
        seg_idx = seg_count - 1
        seg_t = 1.0

    x0, y0 = path[seg_idx]
    x1, y1 = path[seg_idx + 1]

    nx = enemy.dive_start_x + x0 + (x1 - x0) * seg_t
    ny = enemy.dive_start_y + y0 + (y1 - y0) * seg_t

    # Clamp to screen bounds (camera coords)
    if nx < -60:
        nx = -60
    elif nx > 60:
        nx = 60

    enemy.node.position.x = nx
    enemy.node.position.y = ny
    return False


def maybe_trigger_dive(formation, level, dt):
    """Periodically select an enemy to dive. Returns the enemy if one started, else None."""
    formation.dive_timer -= dt
    if formation.dive_timer > 0:
        return None

    formation.dive_timer = level.dive_interval

    diving_count = len(formation.get_diving_enemies())
    if diving_count >= level.max_divers:
        return None

    candidates = formation.get_alive_in_formation()
    if not candidates:
        return None

    enemy = random.choice(candidates)
    start_dive(enemy, formation)
    return enemy
