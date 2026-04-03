from constants import *


class LevelData:
    def __init__(self):
        self.stage = 1
        self.dive_interval = 3.0
        self.dive_speed = DIVE_SPEED_BASE
        self.enemy_fire_chance = 0.015
        self.max_enemy_bullets = 3
        self.max_divers = 1
        self.entry_speed = 1.0
        self.enemy_bullet_speed = ENEMY_BULLET_SPEED

    def set_stage(self, stage):
        self.stage = stage
        # Difficulty ramp: gets harder up to stage 20, then plateaus
        t = min(stage / 20.0, 1.0)

        self.dive_interval = 3.0 - t * 2.0           # 3.0s → 1.0s
        self.dive_speed = DIVE_SPEED_BASE + t * 0.5   # 0.4 → 0.9
        self.enemy_fire_chance = 0.015 + t * 0.045    # 1.5% → 6% per frame
        self.max_enemy_bullets = 3 + int(t * 5)       # 3 → 8
        self.max_divers = 1 + int(t * 3)              # 1 → 4
        self.entry_speed = 1.0 + t * 0.5              # 1.0 → 1.5
        self.enemy_bullet_speed = ENEMY_BULLET_SPEED + t * 40  # 60 → 100

    def is_challenge_stage(self):
        """Stage 3 and every 4th stage after (3, 7, 11, 15, 19...)."""
        return self.stage >= 3 and (self.stage - 3) % 4 == 0
