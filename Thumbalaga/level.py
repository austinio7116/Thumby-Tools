from constants import *

# Based on Galaga Z80 disassembly:
# - Original stage 1 is already active — enemies dive quickly
# - Bomber launch timers: 9,7,5 down to 2,2,2 (roughly 2x speedup)
# - Stage 8+ major aggression jump
# - Max 12 concurrent flyers in original


class LevelData:
    def __init__(self):
        self.stage = 1
        self.dive_interval = 2.0
        self.dive_speed = 0.5
        self.enemy_fire_chance = 0.02
        self.max_enemy_bullets = 3
        self.max_divers = 2
        self.entry_speed = 1.0
        self.enemy_bullet_speed = ENEMY_BULLET_SPEED

    def set_stage(self, stage):
        self.stage = stage

        # 4 tiers: 1-2 (intro), 3-7 (normal), 8-14 (hard), 15+ (brutal)
        if stage <= 2:
            tier = 0
        elif stage <= 7:
            tier = 1
        elif stage <= 14:
            tier = 2
        else:
            tier = 3

        # Dive interval: time between dive attacks
        # Original stage 1 has ~2s between dives
        self.dive_interval = [2.0, 1.5, 0.9, 0.5][tier]

        # Dive speed: path traversal rate (1.0 = full path in 1 second)
        # Original enemies dive fairly fast even on stage 1
        self.dive_speed = [0.5, 0.6, 0.75, 0.95][tier]

        # Fire chance per frame per diving enemy
        self.enemy_fire_chance = [0.02, 0.035, 0.055, 0.08][tier]

        # Max enemy bullets on screen
        self.max_enemy_bullets = [3, 5, 6, 8][tier]

        # Max simultaneous divers
        self.max_divers = [2, 3, 4, 6][tier]

        # Entry fly-in speed
        self.entry_speed = [1.2, 1.4, 1.6, 1.8][tier]

        # Enemy bullet speed
        self.enemy_bullet_speed = [65, 80, 95, 110][tier]

    def is_challenge_stage(self):
        """Stage 3 and every 4th stage after (3, 7, 11, 15, 19...)."""
        return self.stage >= 3 and (self.stage - 3) % 4 == 0
