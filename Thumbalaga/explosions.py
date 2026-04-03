from constants import *


class ExplosionManager:
    """Manages a pool of explosion Sprite2DNodes."""

    def __init__(self, nodes):
        """nodes: list of pre-created Sprite2DNodes with explosion texture."""
        self.nodes = nodes
        self.timers = [0.0] * len(nodes)
        self.active = [False] * len(nodes)
        self.duration = EXPLOSION_FRAMES / EXPLOSION_FPS

    def spawn(self, x, y):
        """Start an explosion at screen position (x, y)."""
        for i in range(len(self.nodes)):
            if not self.active[i]:
                self.active[i] = True
                self.timers[i] = self.duration
                node = self.nodes[i]
                node.position.x = x
                node.position.y = y
                node.opacity = 1.0
                node.frame_current_x = 0
                node.playing = True
                node.loop = False
                return
        # All slots full — skip this explosion

    @micropython.native
    def update(self, dt):
        """Update explosion timers and hide finished ones."""
        for i in range(len(self.nodes)):
            if self.active[i]:
                self.timers[i] -= dt
                if self.timers[i] <= 0:
                    self.active[i] = False
                    self.nodes[i].opacity = 0.0
                    self.nodes[i].playing = False
