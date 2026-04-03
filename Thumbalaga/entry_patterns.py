from constants import *

# Entry paths: sequences of (x, y) screen coordinates that enemies fly through
# before reaching their formation slot. Each path defines an approach route.

# Entry paths use camera coordinates (-64 to +64)

# From top-left, curving to center
PATH_TOP_LEFT = [
    (-74, -74),
    (-44, -49),
    (-19, -29),
    (0, -14),
]

# From top-right, curving to center
PATH_TOP_RIGHT = [
    (74, -74),
    (44, -49),
    (19, -29),
    (0, -14),
]

# From bottom-left, looping up
PATH_BOTTOM_LEFT = [
    (-74, 36),
    (-44, 16),
    (-34, -14),
    (-14, -34),
    (0, -19),
]

# From bottom-right, looping up
PATH_BOTTOM_RIGHT = [
    (74, 36),
    (44, 16),
    (34, -14),
    (14, -34),
    (0, -19),
]

# Straight down from top
PATH_TOP_CENTER = [
    (0, -74),
    (0, -44),
    (0, -19),
]

# Entry wave definition:
# Each group: (delay_seconds, path, [(col, row), ...], spacing_between_enemies)
# spacing: time delay between successive enemies in the group

def get_entry_pattern(stage):
    """Return entry groups for the given stage."""
    # Alternate between two base patterns, speed increases with stage
    if stage % 2 == 1:
        return _pattern_a()
    else:
        return _pattern_b()


def _pattern_a():
    """Pattern A: enemies enter from top-left and top-right alternately."""
    return [
        # Bottom row left half - from top-left
        {
            'delay': 0.0,
            'path': PATH_TOP_LEFT,
            'slots': [(0, 4), (1, 4), (2, 4), (3, 4)],
            'spacing': 0.20,
        },
        # Bottom row right half - from top-right
        {
            'delay': 0.8,
            'path': PATH_TOP_RIGHT,
            'slots': [(4, 4), (5, 4), (6, 4), (7, 4)],
            'spacing': 0.20,
        },
        # Row 3 left - from top-right
        {
            'delay': 1.6,
            'path': PATH_TOP_RIGHT,
            'slots': [(0, 3), (1, 3), (2, 3), (3, 3)],
            'spacing': 0.20,
        },
        # Row 3 right - from top-left
        {
            'delay': 2.4,
            'path': PATH_TOP_LEFT,
            'slots': [(4, 3), (5, 3), (6, 3), (7, 3)],
            'spacing': 0.20,
        },
        # Row 2 - from bottom-left
        {
            'delay': 3.2,
            'path': PATH_BOTTOM_LEFT,
            'slots': [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2)],
            'spacing': 0.18,
        },
        # Row 1 - from bottom-right
        {
            'delay': 4.2,
            'path': PATH_BOTTOM_RIGHT,
            'slots': [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)],
            'spacing': 0.18,
        },
        # Bosses - from top center
        {
            'delay': 5.2,
            'path': PATH_TOP_CENTER,
            'slots': [(2, 0), (3, 0), (4, 0), (5, 0)],
            'spacing': 0.15,
        },
    ]


def _pattern_b():
    """Pattern B: enemies enter from sides in a pincer formation."""
    return [
        # Row 4 - simultaneous from both sides
        {
            'delay': 0.0,
            'path': PATH_BOTTOM_LEFT,
            'slots': [(0, 4), (1, 4), (2, 4), (3, 4)],
            'spacing': 0.18,
        },
        {
            'delay': 0.0,
            'path': PATH_BOTTOM_RIGHT,
            'slots': [(4, 4), (5, 4), (6, 4), (7, 4)],
            'spacing': 0.18,
        },
        # Row 3 from both sides
        {
            'delay': 1.0,
            'path': PATH_TOP_LEFT,
            'slots': [(0, 3), (1, 3), (2, 3), (3, 3)],
            'spacing': 0.18,
        },
        {
            'delay': 1.0,
            'path': PATH_TOP_RIGHT,
            'slots': [(4, 3), (5, 3), (6, 3), (7, 3)],
            'spacing': 0.18,
        },
        # Butterflies row 2 from top
        {
            'delay': 2.0,
            'path': PATH_TOP_LEFT,
            'slots': [(0, 2), (1, 2), (2, 2), (3, 2)],
            'spacing': 0.20,
        },
        {
            'delay': 2.0,
            'path': PATH_TOP_RIGHT,
            'slots': [(4, 2), (5, 2), (6, 2), (7, 2)],
            'spacing': 0.20,
        },
        # Butterflies row 1
        {
            'delay': 3.0,
            'path': PATH_BOTTOM_LEFT,
            'slots': [(0, 1), (1, 1), (2, 1), (3, 1)],
            'spacing': 0.20,
        },
        {
            'delay': 3.0,
            'path': PATH_BOTTOM_RIGHT,
            'slots': [(4, 1), (5, 1), (6, 1), (7, 1)],
            'spacing': 0.20,
        },
        # Bosses from top
        {
            'delay': 4.2,
            'path': PATH_TOP_CENTER,
            'slots': [(2, 0), (3, 0), (4, 0), (5, 0)],
            'spacing': 0.18,
        },
    ]


class EntryState:
    """Tracks entry animation progress."""
    def __init__(self, pattern):
        self.pattern = pattern
        self.time = 0.0

    def reset(self, pattern):
        self.pattern = pattern
        self.time = 0.0


@micropython.native
def interpolate_path(path, t):
    """Interpolate position along a path at parameter t (0-1)."""
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
def update_entry(entry_state, formation, dt, entry_speed=1.0):
    """Update entry animation. Returns True when all enemies are in formation."""
    entry_state.time += dt * entry_speed
    all_done = True

    for group in entry_state.pattern:
        group_delay = group['delay']
        if entry_state.time < group_delay:
            all_done = False
            continue

        path = group['path']
        spacing = group['spacing']

        for i, (col, row) in enumerate(group['slots']):
            idx = row * FORM_COLS + col
            e = formation.enemies[idx]
            if e is None or not e.alive:
                continue

            if e.entry_done and e.in_formation:
                continue  # already settled

            all_done = False

            enemy_time = entry_state.time - group_delay - i * spacing
            if enemy_time < 0:
                continue  # not started yet

            if e.node.opacity < 0.5:
                e.node.opacity = 1.0

            t = enemy_time / ENTRY_DURATION
            if t >= 1.0:
                # Path traversal done — lerp to formation slot
                lerp_t = (enemy_time - ENTRY_DURATION) / ENTRY_LERP_DURATION
                if lerp_t >= 1.0:
                    # Fully in formation
                    e.in_formation = True
                    e.entry_done = True
                    sx, sy = formation.get_slot_screen_pos(col, row)
                    e.node.position.x = sx
                    e.node.position.y = sy
                else:
                    # Lerp from path end to formation slot
                    end_x, end_y = path[-1]
                    slot_x, slot_y = formation.get_slot_screen_pos(col, row)
                    e.node.position.x = end_x + (slot_x - end_x) * lerp_t
                    e.node.position.y = end_y + (slot_y - end_y) * lerp_t
            else:
                # Still on entry path
                px, py = interpolate_path(path, t)
                e.node.position.x = px
                e.node.position.y = py

    return all_done
