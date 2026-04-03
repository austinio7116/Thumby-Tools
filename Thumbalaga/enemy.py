from constants import *


class Enemy:
    __slots__ = ('node', 'type', 'hp', 'slot_col', 'slot_row',
                 'state', 'dive_t', 'dive_path', 'dive_start_x',
                 'dive_start_y', 'in_formation', 'alive',
                 'entry_t', 'entry_path', 'entry_done',
                 'fire_timer', 'escorts', 'is_escort', '_last_x',
                 'hit_flash', '_orig_type')

    def __init__(self):
        self.node = None
        self.type = ENEMY_BEE
        self.hp = 1
        self.slot_col = 0
        self.slot_row = 0
        self.in_formation = False
        self.alive = False
        self.dive_t = 0.0
        self.dive_path = None
        self.dive_start_x = 0.0
        self.dive_start_y = 0.0
        self.entry_t = 0.0
        self.entry_path = None
        self.entry_done = False
        self.fire_timer = 0.0
        self.escorts = []
        self.is_escort = False
        self._last_x = 0.0
        self.hit_flash = 0.0    # countdown: >0 means showing dying palette
        self._orig_type = ENEMY_BEE

    def init_for_stage(self, etype, col, row, node):
        self.type = etype
        self.hp = ENEMY_HP[etype]
        self.slot_col = col
        self.slot_row = row
        self.node = node
        self.alive = True
        self.in_formation = False
        self.entry_done = False
        self.entry_t = -1.0  # not started yet
        self.dive_t = 0.0
        self.dive_path = None
        self.fire_timer = 0.0
        self.escorts = []
        self.is_escort = False
        self._last_x = -200.0
        self.hit_flash = 0.0
        self._orig_type = etype
        node.frame_current_y = etype
        node.frame_current_x = 6  # facing-down idle frame
        node.opacity = 0.0  # hidden until entry begins
        node.position.x = -200
        node.position.y = -200

    def start_dying(self):
        """Show dying palette. Node stays visible briefly, then kill() hides it."""
        self.alive = False  # count as dead immediately for stage clear checks
        if self.node and self._orig_type in DYING_PALETTE:
            self.node.frame_current_y = DYING_PALETTE[self._orig_type]
        self.hit_flash = 0.12  # seconds to show dying palette before hiding

    def update_flash(self, dt):
        """Update hit flash timer. Returns True if flash expired (ready to hide)."""
        if self.hit_flash > 0:
            self.hit_flash -= dt
            if self.hit_flash <= 0:
                self.hit_flash = 0
                self.kill()
                return True
        return False

    def kill(self):
        self.alive = False
        self.hit_flash = 0
        if self.node:
            self.node.opacity = 0.0

    def get_screen_x(self):
        if self.node:
            return self.node.position.x
        return 0.0

    def get_screen_y(self):
        if self.node:
            return self.node.position.y
        return 0.0
