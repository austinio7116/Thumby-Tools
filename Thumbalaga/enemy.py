from constants import *


class Enemy:
    __slots__ = ('node', 'type', 'hp', 'slot_col', 'slot_row',
                 'state', 'dive_t', 'dive_path', 'dive_start_x',
                 'dive_start_y', 'in_formation', 'alive',
                 'entry_t', 'entry_path', 'entry_done',
                 'fire_timer')

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
        node.frame_current_y = etype
        node.frame_current_x = 6  # facing-down idle frame
        node.opacity = 0.0  # hidden until entry begins
        node.position.x = -200
        node.position.y = -200

    def kill(self):
        self.alive = False
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
