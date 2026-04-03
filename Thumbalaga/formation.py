from constants import *
import math


class Formation:
    def __init__(self):
        self.enemies = [None] * (FORM_COLS * FORM_ROWS)
        self.sway_offset = 0.0
        self.sway_dir = 1
        self.alive_count = 0
        self.dive_timer = 3.0
        self.breath_time = 0.0  # for breathing animation

    def reset(self):
        for i in range(FORM_COLS * FORM_ROWS):
            self.enemies[i] = None
        self.sway_offset = 0.0
        self.sway_dir = 1
        self.alive_count = 0
        self.dive_timer = 3.0
        self.breath_time = 0.0

    def set_enemy(self, col, row, enemy):
        self.enemies[row * FORM_COLS + col] = enemy

    def get_enemy(self, col, row):
        return self.enemies[row * FORM_COLS + col]

    @micropython.native
    def get_slot_screen_pos(self, col, row):
        """Return screen (x, y) for a formation slot."""
        breath = math.sin(self.breath_time * 0.8) * 1.0
        sx = FORM_SPACING_X + breath
        sy = FORM_SPACING_Y + breath * 0.5
        center_col = (FORM_COLS - 1) * 0.5
        center_row = (FORM_ROWS - 1) * 0.5
        cx = FORM_ORIGIN_X + center_col * FORM_SPACING_X
        cy = FORM_ORIGIN_Y + center_row * FORM_SPACING_Y
        x = cx + (col - center_col) * sx + self.sway_offset
        y = cy + (row - center_row) * sy
        return x, y

    @micropython.native
    def update(self, dt):
        """Update formation sway, breathing, and reposition in-formation enemies."""
        self.sway_offset += SWAY_SPEED * self.sway_dir * dt
        if self.sway_offset > SWAY_RANGE:
            self.sway_offset = SWAY_RANGE
            self.sway_dir = -1
        elif self.sway_offset < -SWAY_RANGE:
            self.sway_offset = -SWAY_RANGE
            self.sway_dir = 1

        self.breath_time += dt

        breath = math.sin(self.breath_time * 0.8) * 1.0
        sx = FORM_SPACING_X + breath
        sy = FORM_SPACING_Y + breath * 0.5

        # Center the breathing — expand outward from formation center
        center_col = (FORM_COLS - 1) * 0.5  # 3.5
        center_row = (FORM_ROWS - 1) * 0.5  # 2.0
        # Base center position (no breath)
        cx = FORM_ORIGIN_X + center_col * FORM_SPACING_X
        cy = FORM_ORIGIN_Y + center_row * FORM_SPACING_Y

        for i in range(FORM_COLS * FORM_ROWS):
            e = self.enemies[i]
            if e is not None and e.alive and e.in_formation:
                col = i % FORM_COLS
                row = i // FORM_COLS
                e.node.position.x = cx + (col - center_col) * sx + self.sway_offset
                e.node.position.y = cy + (row - center_row) * sy

    def count_alive(self):
        count = 0
        for e in self.enemies:
            if e is not None and e.alive:
                count += 1
        self.alive_count = count
        return count

    def get_alive_in_formation(self):
        result = []
        for e in self.enemies:
            if e is not None and e.alive and e.in_formation:
                result.append(e)
        return result

    def get_diving_enemies(self):
        result = []
        for e in self.enemies:
            if e is not None and e.alive and not e.in_formation and e.entry_done:
                result.append(e)
        return result
