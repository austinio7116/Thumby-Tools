import engine_draw
from constants import *


class HUD:
    def __init__(self):
        self.score = 0
        self.high_score = 0
        self.lives = START_LIVES
        self.stage = 1
        self._score_str = "0"
        self._stage_str = "1"

    def add_score(self, points):
        self.score += points
        self._score_str = str(self.score)
        if self.score > self.high_score:
            self.high_score = self.score

    def set_stage(self, stage):
        self.stage = stage
        self._stage_str = str(stage)

    def reset(self):
        self.score = 0
        self._score_str = "0"
        self.lives = START_LIVES
        self.stage = 1
        self._stage_str = "1"

    def draw(self, fb):
        """Draw HUD elements. engine_draw.text uses screen coords (0-127)."""
        # engine_draw.text(font, text, color, x, y, letter_spacing, line_spacing, opacity)
        # None for font uses the built-in default font
        engine_draw.text(None, self._score_str, None, 2, 1, 1, 0, 1.0)
        engine_draw.text(None, "S" + self._stage_str, None, 100, 1, 1, 0, 1.0)

        # Lives at bottom-left: small colored rectangles
        for i in range(self.lives):
            fb.rect(3 + i * 8, 122, 5, 5, COL_CYAN, True)

    def draw_centered_text(self, text, screen_y):
        """Draw centered text at screen Y coordinate."""
        x = max(0, 64 - len(text) * 3)
        engine_draw.text(None, text, None, x, screen_y, 1, 0, 1.0)

    def draw_title(self, fb):
        """Draw title screen."""
        engine_draw.text(None, "THUMBALAGA", None, 24, 35, 1, 0, 1.0)
        engine_draw.text(None, "PRESS .", None, 40, 75, 1, 0, 1.0)
        engine_draw.text(None, "HI " + str(self.high_score), None, 38, 55, 1, 0, 1.0)

    def draw_game_over(self, fb):
        """Draw game over screen."""
        engine_draw.text(None, "GAME OVER", None, 30, 45, 1, 0, 1.0)
        engine_draw.text(None, "SCORE " + self._score_str, None, 28, 65, 1, 0, 1.0)
        engine_draw.text(None, "PRESS .", None, 40, 85, 1, 0, 1.0)
