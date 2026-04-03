"""Transform enemies: a bee morphs into 3 special enemies that dive through and exit.
They fire bullets on the way down. Always 3 of the same type.
Scorpions (stages 4-6, 1000 pts), Bosconians (7-9, 2000 pts), Galaxians (10-12, 3000 pts).
Cycle repeats. Each individual kill = 160 pts.
Pre-morph: bee pulsates through colors for ~1s before transforming."""

import random
from constants import *
from constants import get_idle_frames


def get_transform_type(stage):
    if stage < 4:
        return None
    cycle = ((stage - 4) // 3) % 3
    return [ENEMY_SCORPION, ENEMY_BOSCONIAN, ENEMY_GALAXIAN][cycle]


def get_transform_bonus(stage):
    if stage < 4:
        return 0
    cycle = ((stage - 4) // 3) % 3
    return [1000, 2000, 3000][cycle]


TRANSFORM_INDIVIDUAL_PTS = const(160)

TRANSFORM_PATH_LEFT = [
    (0, 0), (-20, 25), (-30, 55), (-15, 85), (5, 110), (0, 145),
]
TRANSFORM_PATH_RIGHT = [
    (0, 0), (20, 25), (30, 55), (15, 85), (-5, 110), (0, 145),
]
TRANSFORM_PATH_CENTER = [
    (0, 0), (-8, 30), (12, 60), (-8, 90), (5, 120), (0, 145),
]
TRANSFORM_PATHS = [TRANSFORM_PATH_LEFT, TRANSFORM_PATH_RIGHT, TRANSFORM_PATH_CENTER]
TRANSFORM_SPREAD = const(14)

# Pre-morph pulsation: cycle through color rows
PREMORPH_DURATION = 1.0  # seconds to pulsate before morphing
PREMORPH_COLORS = [ENEMY_BEE, ENEMY_PRETRANSFORM, ENEMY_BEE_DYING,
                   ENEMY_PRETRANSFORM, ENEMY_BEE, ENEMY_PRETRANSFORM]


class TransformGroup:
    __slots__ = ('enemies', 'path', 'start_x', 'start_y', 't',
                 'active', 'kills', 'bonus', 'speed', 'fire_timer')

    def __init__(self):
        self.enemies = []
        self.path = None
        self.start_x = 0.0
        self.start_y = 0.0
        self.t = 0.0
        self.active = False
        self.kills = 0
        self.bonus = 0
        self.speed = 0.45
        self.fire_timer = 0.0


class TransformManager:
    def __init__(self):
        self.groups = []
        self.morph_timer = 0.0
        self.morph_interval = 8.0
        # Pre-morph state
        self.premorph_bee = None       # the bee that's pulsating
        self.premorph_timer = 0.0
        self.premorph_stage = 0
        self.premorph_ttype = None

    def reset(self):
        self.groups = []
        self.morph_timer = 5.0
        self.premorph_bee = None
        self.premorph_timer = 0.0

    @micropython.native
    def try_morph(self, formation, stage, enemy_nodes, dt):
        ttype = get_transform_type(stage)
        if ttype is None:
            return None

        # Handle pre-morph pulsation
        if self.premorph_bee is not None:
            self.premorph_timer -= dt
            if self.premorph_timer > 0:
                # Cycle through color palettes
                phase = int((PREMORPH_DURATION - self.premorph_timer) / PREMORPH_DURATION * len(PREMORPH_COLORS))
                phase = min(phase, len(PREMORPH_COLORS) - 1)
                if self.premorph_bee.node:
                    self.premorph_bee.node.frame_current_y = PREMORPH_COLORS[phase]
                return None  # still pulsating
            else:
                # Pulsation done — do the actual morph
                bee = self.premorph_bee
                self.premorph_bee = None
                return self._do_morph(bee, ttype, stage, enemy_nodes)

        # Check if it's time to start a morph
        self.morph_timer -= dt
        if self.morph_timer > 0:
            return None
        self.morph_timer = self.morph_interval

        # Find a bee in formation to morph
        source_bee = None
        for e in formation.enemies:
            if e is not None and e.alive and e.in_formation and e.type == ENEMY_BEE:
                source_bee = e
                break
        if source_bee is None:
            return None

        # Start pre-morph pulsation
        self.premorph_bee = source_bee
        self.premorph_timer = PREMORPH_DURATION
        self.premorph_ttype = ttype
        self.premorph_stage = stage
        return None  # morph will complete after pulsation

    def _do_morph(self, source_bee, ttype, stage, enemy_nodes):
        """Actually perform the morph after pulsation is done."""
        sx = source_bee.node.position.x
        sy = source_bee.node.position.y
        source_bee.kill()

        # Find 3 unused enemy nodes
        nodes_found = []
        for node in enemy_nodes:
            if node.opacity < 0.1 and len(nodes_found) < 3:
                nodes_found.append(node)
        if len(nodes_found) < 3:
            return None

        group = TransformGroup()
        group.path = random.choice(TRANSFORM_PATHS)
        group.start_x = sx
        group.start_y = sy
        group.t = 0.0
        group.active = True
        group.kills = 0
        group.bonus = get_transform_bonus(stage)
        group.speed = 0.45
        group.fire_timer = random.random() * 0.5 + 0.3

        group.enemies = []
        for i, node in enumerate(nodes_found):
            node.frame_current_y = ttype
            ia, ib = get_idle_frames(ttype)
            node.frame_current_x = ia
            node.opacity = 1.0
            node.position.x = sx + (i - 1) * TRANSFORM_SPREAD
            node.position.y = sy
            node.scale.x = 1.0
            group.enemies.append([node, True])

        self.groups.append(group)
        return group

    @micropython.native
    def update(self, dt, bullet_fire_fn=None):
        finished = []
        for g in self.groups:
            if not g.active:
                continue

            g.t += dt * g.speed
            path = g.path
            seg_count = len(path) - 1

            if g.t >= 1.0:
                g.active = False
                for node, alive in g.enemies:
                    node.opacity = 0.0
                    node.position.x = -200
                    node.position.y = -200
                finished.append(g)
                continue

            # Each enemy follows path independently with diverging offsets
            for i, (node, alive) in enumerate(g.enemies):
                if not alive:
                    continue
                ei_t = g.t - i * 0.06
                if ei_t < 0:
                    ei_t = 0
                t_scaled = ei_t * seg_count
                seg_idx = int(t_scaled)
                seg_t = t_scaled - seg_idx
                if seg_idx >= seg_count:
                    seg_idx = seg_count - 1
                    seg_t = 1.0

                x0, y0 = path[seg_idx]
                x1, y1 = path[seg_idx + 1]
                cx = g.start_x + x0 + (x1 - x0) * seg_t
                cy = g.start_y + y0 + (y1 - y0) * seg_t

                spread = (i - 1) * TRANSFORM_SPREAD * (0.5 + g.t)
                node.position.x = cx + spread
                node.position.y = cy

            # Fire bullets periodically
            if bullet_fire_fn:
                g.fire_timer -= dt
                if g.fire_timer <= 0:
                    g.fire_timer = random.random() * 0.8 + 0.4
                    alive_nodes = [n for n, a in g.enemies if a]
                    if alive_nodes:
                        shooter = random.choice(alive_nodes)
                        bullet_fire_fn(shooter.position.x, shooter.position.y)

        self.groups = [g for g in self.groups if g.active]
        return finished

    def check_bullet_hit(self, bx, by):
        for g in self.groups:
            if not g.active:
                continue
            for i, (node, alive) in enumerate(g.enemies):
                if not alive:
                    continue
                if abs(bx - node.position.x) < ENEMY_HALF + 1 and \
                   abs(by - node.position.y) < ENEMY_HALF + 2:
                    return (g, i)
        return None

    def check_player_collision(self, px, py):
        for g in self.groups:
            if not g.active:
                continue
            for i, (node, alive) in enumerate(g.enemies):
                if not alive:
                    continue
                if abs(px - node.position.x) < ENEMY_HALF + PLAYER_HALF_W - 2 and \
                   abs(py - node.position.y) < ENEMY_HALF + PLAYER_HALF_H - 2:
                    return (g, i)
        return None

    def kill_enemy(self, group, index):
        node, _ = group.enemies[index]
        group.enemies[index] = [node, False]
        node.opacity = 0.0
        node.position.x = -200
        node.position.y = -200
        group.kills += 1
