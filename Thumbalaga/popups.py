"""Floating score popups — briefly show point values where enemies die."""

import engine_draw
from constants import *

MAX_POPUPS = const(6)
POPUP_DURATION = 0.8  # seconds


class ScorePopups:
    def __init__(self):
        self.texts = [""] * MAX_POPUPS
        self.x = [0] * MAX_POPUPS
        self.y = [0] * MAX_POPUPS
        self.timers = [0.0] * MAX_POPUPS
        self.active = [False] * MAX_POPUPS

    def spawn(self, text, cam_x, cam_y):
        """Show a score popup at camera coordinates."""
        for i in range(MAX_POPUPS):
            if not self.active[i]:
                self.texts[i] = str(text)
                # Convert camera to screen coords
                self.x[i] = int(cam_x + 64) - len(self.texts[i]) * 3
                self.y[i] = int(cam_y + 64) - 4
                self.timers[i] = POPUP_DURATION
                self.active[i] = True
                return

    @micropython.native
    def update_and_draw(self, dt):
        """Update timers and draw active popups."""
        for i in range(MAX_POPUPS):
            if not self.active[i]:
                continue
            self.timers[i] -= dt
            if self.timers[i] <= 0:
                self.active[i] = False
                continue
            # Float upward
            self.y[i] -= 15 * dt
            # Draw with fade
            opacity = min(1.0, self.timers[i] / 0.3)
            engine_draw.text(None, self.texts[i], None,
                             self.x[i], int(self.y[i]), 1, 0, opacity)
