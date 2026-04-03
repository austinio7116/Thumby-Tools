from constants import *


class Formation:
    def __init__(self):
        self.enemies = [None] * (FORM_COLS * FORM_ROWS)
        self.sway_offset = 0.0
        self.sway_dir = 1
        self.alive_count = 0
        self.dive_timer = 3.0

    def reset(self):
        for i in range(FORM_COLS * FORM_ROWS):
            self.enemies[i] = None
        self.sway_offset = 0.0
        self.sway_dir = 1
        self.alive_count = 0
        self.dive_timer = 3.0

    def set_enemy(self, col, row, enemy):
        self.enemies[row * FORM_COLS + col] = enemy

    def get_enemy(self, col, row):
        return self.enemies[row * FORM_COLS + col]

    @micropython.native
    def get_slot_screen_pos(self, col, row):
        """Return screen (x, y) for a formation slot."""
        x = FORM_ORIGIN_X + col * FORM_SPACING_X + self.sway_offset
        y = FORM_ORIGIN_Y + row * FORM_SPACING_Y
        return x, y

    @micropython.native
    def update(self, dt):
        """Update formation sway and reposition in-formation enemies."""
        self.sway_offset += SWAY_SPEED * self.sway_dir * dt
        if self.sway_offset > SWAY_RANGE:
            self.sway_offset = SWAY_RANGE
            self.sway_dir = -1
        elif self.sway_offset < -SWAY_RANGE:
            self.sway_offset = -SWAY_RANGE
            self.sway_dir = 1

        for i in range(FORM_COLS * FORM_ROWS):
            e = self.enemies[i]
            if e is not None and e.alive and e.in_formation:
                col = i % FORM_COLS
                row = i // FORM_COLS
                e.node.position.x = FORM_ORIGIN_X + col * FORM_SPACING_X + self.sway_offset
                e.node.position.y = FORM_ORIGIN_Y + row * FORM_SPACING_Y

    def count_alive(self):
        count = 0
        for e in self.enemies:
            if e is not None and e.alive:
                count += 1
        self.alive_count = count
        return count

    def get_alive_in_formation(self):
        """Return list of enemies currently in formation (for dive selection)."""
        result = []
        for e in self.enemies:
            if e is not None and e.alive and e.in_formation:
                result.append(e)
        return result

    def get_diving_enemies(self):
        """Return list of enemies currently diving."""
        result = []
        for e in self.enemies:
            if e is not None and e.alive and not e.in_formation and e.entry_done:
                result.append(e)
        return result
