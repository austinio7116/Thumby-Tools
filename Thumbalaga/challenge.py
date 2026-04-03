"""Challenging Stage: 5 waves of 8 enemies fly through in looping
patterns without shooting. 100 pts per kill, 10000 bonus for perfect (40/40)."""

from constants import *
from constants import get_idle_frames
import random

# Challenge flight paths — enemies fly IN, loop/swoop across screen, fly OUT.
# Coordinates are in camera space (-64 to +64).
# Each path is a list of (x, y) waypoints.

# Wave 1: Enter top-right, loop left, exit top-left
PATH_LOOP_RIGHT_TO_LEFT = [
    (80, -70),       # start off-screen top-right
    (40, -30),
    (10, 0),
    (-20, 15),
    (-40, 0),
    (-20, -20),
    (10, -10),
    (30, 10),
    (10, 30),
    (-30, 20),
    (-70, -30),      # exit off-screen left
]

# Wave 2: Enter top-left, loop right, exit top-right
PATH_LOOP_LEFT_TO_RIGHT = [
    (-80, -70),
    (-40, -30),
    (-10, 0),
    (20, 15),
    (40, 0),
    (20, -20),
    (-10, -10),
    (-30, 10),
    (-10, 30),
    (30, 20),
    (70, -30),
]

# Wave 3: Enter top-center, figure-8 pattern, exit bottom
PATH_FIGURE_8 = [
    (0, -70),
    (30, -35),
    (40, -5),
    (20, 15),
    (0, 5),
    (-20, 15),
    (-40, -5),
    (-30, -35),
    (0, -15),
    (25, 5),
    (35, 30),
    (10, 50),
    (0, 75),
]

# Wave 4: Enter from right, swooping S-curve, exit left
PATH_S_CURVE_RIGHT = [
    (80, -20),
    (40, -10),
    (10, 10),
    (-20, -10),
    (-40, 15),
    (-10, 35),
    (20, 20),
    (40, 40),
    (10, 55),
    (-40, 40),
    (-80, 20),
]

# Wave 5: Enter from left, swooping S-curve, exit right
PATH_S_CURVE_LEFT = [
    (-80, -20),
    (-40, -10),
    (-10, 10),
    (20, -10),
    (40, 15),
    (10, 35),
    (-20, 20),
    (-40, 40),
    (-10, 55),
    (40, 40),
    (80, 20),
]

ALL_WAVE_PATHS = [
    PATH_LOOP_RIGHT_TO_LEFT,
    PATH_LOOP_LEFT_TO_RIGHT,
    PATH_FIGURE_8,
    PATH_S_CURVE_RIGHT,
    PATH_S_CURVE_LEFT,
]

CHALLENGE_WAVE_COUNT = const(5)
CHALLENGE_ENEMIES_PER_WAVE = const(8)
CHALLENGE_TOTAL = const(40)  # 5 * 8
CHALLENGE_ENEMY_SPACING = 0.15  # seconds between enemies in a wave
CHALLENGE_WAVE_DELAY = 2.5  # seconds between waves
CHALLENGE_PATH_DURATION = 2.0  # seconds to traverse path
CHALLENGE_PERFECT_BONUS = const(10000)
CHALLENGE_HIT_POINTS = const(100)


class ChallengeWaveEnemy:
    """A single enemy in a challenge wave."""
    __slots__ = ('node', 'path', 'start_time', 'active', 'alive', 'finished', 'wave_idx')

    def __init__(self):
        self.node = None
        self.path = None
        self.start_time = 0.0
        self.active = False
        self.alive = True
        self.finished = False
        self.wave_idx = 0


class ChallengeState:
    """Manages the challenging stage."""

    def __init__(self):
        self.enemies = []
        self.wave_kills = [0] * CHALLENGE_WAVE_COUNT
        self.wave_done = [False] * CHALLENGE_WAVE_COUNT
        self.time = 0.0
        self.kills = 0
        self.total_spawned = 0
        self.all_done = False

    def init(self, enemy_nodes):
        """Set up 5 waves of 8 enemies using the node pool."""
        self.enemies = []
        self.time = 0.0
        self.kills = 0
        self.total_spawned = 0
        self.all_done = False
        self.wave_kills = [0] * CHALLENGE_WAVE_COUNT
        self.wave_done = [False] * CHALLENGE_WAVE_COUNT

        # Each wave uses the same enemy type — challenge-exclusive enemies
        # Dragonfly, Satellite, Enterprise cycle, plus Bee and Butterfly
        wave_types = [ENEMY_DRAGONFLY, ENEMY_SATELLITE, ENEMY_ENTERPRISE,
                      ENEMY_DRAGONFLY, ENEMY_SATELLITE]

        node_idx = 0
        for wave_idx in range(CHALLENGE_WAVE_COUNT):
            path = ALL_WAVE_PATHS[wave_idx % len(ALL_WAVE_PATHS)]
            wave_start = wave_idx * CHALLENGE_WAVE_DELAY
            wave_enemy_type = wave_types[wave_idx % len(wave_types)]

            for i in range(CHALLENGE_ENEMIES_PER_WAVE):
                if node_idx >= len(enemy_nodes):
                    break
                ce = ChallengeWaveEnemy()
                ce.node = enemy_nodes[node_idx]
                ce.path = path
                ce.start_time = wave_start + i * CHALLENGE_ENEMY_SPACING
                ce.active = False
                ce.alive = True
                ce.finished = False
                ce.wave_idx = wave_idx

                # All enemies in this wave are the same type
                ce.node.frame_current_y = wave_enemy_type
                ia, ib = get_idle_frames(wave_enemy_type)
                ce.node.frame_current_x = ia
                ce.node.playing = False
                ce.node.opacity = 0.0
                ce.node.position.x = -200
                ce.node.position.y = -200

                self.enemies.append(ce)
                node_idx += 1

        self.total_spawned = len(self.enemies)


@micropython.native
def interpolate_challenge_path(path, t):
    """Interpolate position along a challenge path at parameter t (0-1)."""
    seg_count = len(path) - 1
    if seg_count <= 0:
        return path[0][0], path[0][1]

    t_scaled = t * seg_count
    seg_idx = int(t_scaled)
    seg_t = t_scaled - seg_idx

    if seg_idx >= seg_count:
        return path[-1][0], path[-1][1]

    x0, y0 = path[seg_idx]
    x1, y1 = path[seg_idx + 1]

    return x0 + (x1 - x0) * seg_t, y0 + (y1 - y0) * seg_t


@micropython.native
def update_challenge(challenge, dt):
    """Update challenge stage. Returns True when all waves complete."""
    challenge.time += dt
    all_finished = True

    for ce in challenge.enemies:
        if ce.finished:
            continue

        if not ce.alive:
            ce.finished = True
            continue

        all_finished = False

        if challenge.time < ce.start_time:
            continue  # not started yet

        enemy_t = challenge.time - ce.start_time
        t = enemy_t / CHALLENGE_PATH_DURATION

        if t >= 1.0:
            # Exited screen — done
            ce.finished = True
            ce.active = False
            ce.node.opacity = 0.0
            ce.node.position.x = -200
            ce.node.position.y = -200
            continue

        # Make visible and move along path
        if not ce.active:
            ce.active = True
            ce.node.opacity = 1.0

        px, py = interpolate_challenge_path(ce.path, t)
        ce.node.position.x = px
        ce.node.position.y = py

    challenge.all_done = all_finished
    return all_finished
