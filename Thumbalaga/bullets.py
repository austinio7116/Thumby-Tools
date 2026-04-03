from constants import *


class BulletManager:
    """Manages all bullets using flat arrays, renders directly to framebuffer.
    Bullet positions are in camera coordinates (-64 to +64).
    Drawing converts to screen coordinates (0-127)."""

    def __init__(self):
        # Player bullets
        self.p_x = [0.0] * MAX_PLAYER_BULLETS
        self.p_y = [0.0] * MAX_PLAYER_BULLETS
        self.p_active = [False] * MAX_PLAYER_BULLETS

        # Enemy bullets
        self.e_x = [0.0] * MAX_ENEMY_BULLETS
        self.e_y = [0.0] * MAX_ENEMY_BULLETS
        self.e_active = [False] * MAX_ENEMY_BULLETS

    def clear_all(self):
        for i in range(MAX_PLAYER_BULLETS):
            self.p_active[i] = False
        for i in range(MAX_ENEMY_BULLETS):
            self.e_active[i] = False

    def fire_player(self, x, y):
        """Fire a player bullet. Returns True if fired."""
        for i in range(MAX_PLAYER_BULLETS):
            if not self.p_active[i]:
                self.p_x[i] = x
                self.p_y[i] = y - 7  # offset above player
                self.p_active[i] = True
                return True
        return False

    def fire_enemy(self, x, y):
        """Fire an enemy bullet downward. Returns True if fired."""
        for i in range(MAX_ENEMY_BULLETS):
            if not self.e_active[i]:
                self.e_x[i] = x
                self.e_y[i] = y + 5  # offset below enemy
                self.e_active[i] = True
                return True
        return False

    def active_player_bullet_count(self):
        count = 0
        for i in range(MAX_PLAYER_BULLETS):
            if self.p_active[i]:
                count += 1
        return count

    @micropython.native
    def update(self, dt):
        """Move all active bullets."""
        p_speed = PLAYER_BULLET_SPEED * dt
        e_speed = ENEMY_BULLET_SPEED * dt

        for i in range(MAX_PLAYER_BULLETS):
            if self.p_active[i]:
                self.p_y[i] -= p_speed
                if self.p_y[i] < -66:
                    self.p_active[i] = False

        for i in range(MAX_ENEMY_BULLETS):
            if self.e_active[i]:
                self.e_y[i] += e_speed
                if self.e_y[i] > 66:
                    self.e_active[i] = False

    @micropython.native
    def draw(self, fb):
        """Draw bullets to framebuffer (converts camera coords to screen coords)."""
        for i in range(MAX_PLAYER_BULLETS):
            if self.p_active[i]:
                # Camera to screen: add 64 (half screen)
                sx = int(self.p_x[i] + 64) - 1
                sy = int(self.p_y[i] + 64)
                if 0 <= sx < 126 and 0 <= sy < 125:
                    fb.rect(sx, sy, BULLET_W, PLAYER_BULLET_H, COL_WHITE, True)

        for i in range(MAX_ENEMY_BULLETS):
            if self.e_active[i]:
                sx = int(self.e_x[i] + 64) - 1
                sy = int(self.e_y[i] + 64)
                if 0 <= sx < 126 and 0 <= sy < 126:
                    fb.rect(sx, sy, BULLET_W, ENEMY_BULLET_H, COL_RED, True)
