import engine_draw
import engine_save
import framebuf
from engine_draw import Color
from engine_resources import TextureResource
from constants import *


class HUD:
    def __init__(self):
        self.score = 0
        self.high_score = 0
        self.lives = START_LIVES
        self.stage = 1
        self._score_str = "0"
        self._hi_str = "0"
        self._load_high_score()
        # Load sprites
        self.life_tex = self._load("assets/life_icon.bmp")
        self.narrow_tex = self._load("assets/badge_narrow.bmp")
        self.shield_tex = self._load("assets/badge_shields.bmp")
        # Pre-split badge frames into framebuffers
        self.narrow_fbs = self._split_frames(self.narrow_tex, 5, 10, 2)  # 1-flag, 5-badge
        self.shield_fbs = self._split_frames(self.shield_tex, 8, 8, 4)  # 10,20,30,50

    def _load(self, path):
        try:
            return TextureResource(path)
        except:
            return None

    def _split_frames(self, tex, fw, fh, count):
        """Split a horizontal strip texture into individual framebuf objects."""
        if tex is None:
            return []
        fbs = []
        for i in range(count):
            buf = bytearray(fw * fh * 2)
            src = tex.data
            src_w = tex.width
            for y in range(fh):
                for x in range(fw):
                    so = (y * src_w + i * fw + x) * 2
                    do = (y * fw + x) * 2
                    buf[do] = src[so]
                    buf[do + 1] = src[so + 1]
            fbs.append(framebuf.FrameBuffer(buf, fw, fh, framebuf.RGB565))
        return fbs

    def _load_high_score(self):
        try:
            engine_save.set_location("thumbalaga.sav")
            val = engine_save.load("hi", 0)
            if val and int(val) > 0:
                self.high_score = int(val)
                self._hi_str = str(self.high_score)
        except:
            pass

    def _save_high_score(self):
        try:
            engine_save.set_location("thumbalaga.sav")
            engine_save.save("hi", self.high_score)
        except:
            pass

    def add_score(self, points):
        self.score += points
        self._score_str = str(self.score)
        if self.score > self.high_score:
            self.high_score = self.score
            self._hi_str = str(self.high_score)
            self._save_high_score()

    def set_stage(self, stage):
        self.stage = stage

    def reset(self):
        self.score = 0
        self._score_str = "0"
        self.lives = START_LIVES
        self.stage = 1

    def draw(self, fb):
        """Draw HUD — score top-left, high score top-right, badges bottom-right."""
        engine_draw.text(None, self._score_str, None, 2, 1, 1, 0, 1.0)
        engine_draw.text(None, "HI" + self._hi_str, None, 80, 1, 1, 0, 0.6)

        # Lives at bottom-left
        if self.life_tex:
            for i in range(self.lives):
                engine_draw.blit(self.life_tex, 3 + i * 8, 121,
                                 Color(COL_MAGENTA), 1.0)
        else:
            for i in range(self.lives):
                fb.rect(3 + i * 8, 122, 5, 5, COL_CYAN, True)

        # Stage badges at bottom-right
        self._draw_stage_badges(fb)

    def _draw_stage_badges(self, fb):
        """Compose stage number from badge markers: 50, 30, 20, 10, 5, 1s."""
        s = self.stage  # current stage number
        if s <= 0:
            return

        # shields: index 0=10, 1=20, 2=30, 3=50
        # narrow: index 0=1-flag, 1=5-badge
        badges = []  # list of (framebuf, width)

        # Decompose into badge values (largest first, right to left display)
        if s >= 50 and len(self.shield_fbs) > 3:
            count_50 = s // 50
            for _ in range(count_50):
                badges.append((self.shield_fbs[3], 8))
            s %= 50
        if s >= 30 and len(self.shield_fbs) > 2:
            badges.append((self.shield_fbs[2], 8))
            s -= 30
        if s >= 20 and len(self.shield_fbs) > 1:
            badges.append((self.shield_fbs[1], 8))
            s -= 20
        if s >= 10 and len(self.shield_fbs) > 0:
            badges.append((self.shield_fbs[0], 8))
            s -= 10
        if s >= 5 and len(self.narrow_fbs) > 1:
            badges.append((self.narrow_fbs[1], 5))
            s -= 5
        while s > 0 and len(self.narrow_fbs) > 0:
            badges.append((self.narrow_fbs[0], 5))
            s -= 1

        # Draw right-aligned at bottom-right
        x = 126
        for badge_fb, bw in reversed(badges):
            x -= bw + 1
            if x < 50:
                break  # don't overflow into lives area
            fb.blit(badge_fb, x, 120, COL_MAGENTA)

    def draw_centered_text(self, text, screen_y):
        x = max(0, 64 - len(text) * 3)
        engine_draw.text(None, text, None, x, screen_y, 1, 0, 1.0)

    def draw_title(self, fb):
        engine_draw.text(None, "THUMBALAGA", None, 24, 30, 1, 0, 1.0)
        engine_draw.text(None, "HI " + self._hi_str, None, 38, 50, 1, 0, 1.0)
        engine_draw.text(None, "PRESS A", None, 38, 75, 1, 0, 1.0)

    def draw_game_over(self, fb):
        engine_draw.text(None, "GAME OVER", None, 30, 40, 1, 0, 1.0)
        engine_draw.text(None, "SCORE " + self._score_str, None, 28, 58, 1, 0, 1.0)
        if self.score >= self.high_score:
            engine_draw.text(None, "NEW HIGH SCORE!", None, 16, 72, 1, 0, 1.0)
        engine_draw.text(None, "PRESS A", None, 38, 90, 1, 0, 1.0)
