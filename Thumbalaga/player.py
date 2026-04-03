from engine_nodes import Sprite2DNode
from engine_draw import Color
from engine_math import Vector2
from constants import *


class Player(Sprite2DNode):
    def __init__(self, texture):
        super().__init__(self)
        self.texture = texture
        self.transparent_color = Color(COL_MAGENTA)
        self.position = Vector2(PLAYER_START_X, PLAYER_Y)
        self.layer = 10
        self.alive = True
        self.respawn_timer = 0.0
        self.invincible_timer = 0.0
        self.dual_fighter = False  # True = double firepower

    def reset(self):
        self.position.x = PLAYER_START_X
        self.position.y = PLAYER_Y
        self.alive = True
        self.opacity = 1.0
        self.invincible_timer = 2.0
        self.dual_fighter = False

    def rescue_ship(self):
        """Activate dual fighter mode."""
        self.dual_fighter = True

    def is_invincible(self):
        return self.invincible_timer > 0

    @micropython.native
    def update(self, dt, move_left, move_right):
        if not self.alive:
            return

        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            self.opacity = 0.3 if int(self.invincible_timer * 10) % 2 else 1.0
        else:
            self.opacity = 1.0

        if move_left:
            self.position.x = max(-58, self.position.x - PLAYER_SPEED * dt)
        if move_right:
            self.position.x = min(58, self.position.x + PLAYER_SPEED * dt)
