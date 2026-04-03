from constants import *
import framebuf


# Bullet sprite: 6 frames of 6x6 in a horizontal strip (36x6)
# Frame 0: diagonal down-right, 1: vertical down, 2: diagonal down-left
# Frame 3: horizontal right, 4: vertical up, 5: diagonal up-right
BULLET_SPRITE_SIZE = const(6)
BS = const(6)


class BulletManager:
    """Manages all bullets, renders using bullet sprite frames."""

    def __init__(self):
        self.p_x = [0.0] * MAX_PLAYER_BULLETS
        self.p_y = [0.0] * MAX_PLAYER_BULLETS
        self.p_active = [False] * MAX_PLAYER_BULLETS

        self.e_x = [0.0] * MAX_ENEMY_BULLETS
        self.e_y = [0.0] * MAX_ENEMY_BULLETS
        self.e_dx = [0.0] * MAX_ENEMY_BULLETS
        self.e_active = [False] * MAX_ENEMY_BULLETS

        # Individual framebuf per bullet frame
        self.frames = []  # list of (framebuf, bytearray)

    def set_texture(self, texture_resource):
        """Split bullet sprite sheet into individual frame framebufs."""
        self.frames = []
        src_data = texture_resource.data
        src_w = texture_resource.width
        num_frames = src_w // BS

        for f in range(num_frames):
            # Extract BS x BS region from the strip
            buf = bytearray(BS * BS * 2)
            for y in range(BS):
                for x in range(BS):
                    src_offset = (y * src_w + f * BS + x) * 2
                    dst_offset = (y * BS + x) * 2
                    buf[dst_offset] = src_data[src_offset]
                    buf[dst_offset + 1] = src_data[src_offset + 1]
            fb = framebuf.FrameBuffer(buf, BS, BS, framebuf.RGB565)
            self.frames.append(fb)

    def clear_all(self):
        for i in range(MAX_PLAYER_BULLETS):
            self.p_active[i] = False
        for i in range(MAX_ENEMY_BULLETS):
            self.e_active[i] = False

    def fire_player(self, x, y):
        for i in range(MAX_PLAYER_BULLETS):
            if not self.p_active[i]:
                self.p_x[i] = x
                self.p_y[i] = y - 7
                self.p_active[i] = True
                return True
        return False

    def fire_enemy(self, x, y, target_x=0.0):
        for i in range(MAX_ENEMY_BULLETS):
            if not self.e_active[i]:
                self.e_x[i] = x
                self.e_y[i] = y + 5
                self.e_dx[i] = 0.0  # straight down, no angle
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
                self.e_x[i] += self.e_dx[i] * dt
                if self.e_y[i] > 66 or self.e_x[i] < -66 or self.e_x[i] > 66:
                    self.e_active[i] = False

    @micropython.native
    def draw(self, fb):
        has_frames = len(self.frames) >= 5

        # Player bullets — white/silver shaft with red/cyan arrowhead at bottom
        # Original: 4px white shaft, then 3px wide red arrowhead with cyan center
        COL_SILVER = const(0xDEDB)  # (222,222,222)
        for i in range(MAX_PLAYER_BULLETS):
            if self.p_active[i]:
                sx = int(self.p_x[i] + 64)
                sy = int(self.p_y[i] + 64)
                if 1 <= sx < 126 and 0 <= sy < 122:
                    # Silver shaft (top, 1px wide x 4px)
                    fb.vline(sx, sy, 4, COL_SILVER)
                    # Red arrowhead (3px wide x 2px)
                    fb.rect(sx - 1, sy + 4, 3, 2, COL_RED, True)
                    fb.pixel(sx, sy + 4, COL_CYAN)  # cyan center
                    # Red tail tip
                    fb.pixel(sx, sy + 6, COL_RED)

        # Enemy bullets — silver/white shaft with red arrow tip at bottom
        # Original: blue arrowhead at top, red shaft below
        # User wants: silver shaft, red arrow tip
        for i in range(MAX_ENEMY_BULLETS):
            if self.e_active[i]:
                sx = int(self.e_x[i] + 64)
                sy = int(self.e_y[i] + 64)
                if 1 <= sx < 126 and 0 <= sy < 122:
                    # Silver shaft (top, 1px wide x 4px)
                    fb.vline(sx, sy, 4, COL_SILVER)
                    # Red arrow tip (3px wide x 2px)
                    fb.rect(sx - 1, sy + 4, 3, 2, COL_RED, True)
                    # Red point
                    fb.pixel(sx, sy + 6, COL_RED)
