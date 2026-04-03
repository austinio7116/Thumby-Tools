import random
from constants import *


class Starfield:
    def __init__(self, count=18):
        self.count = count
        self.x = [random.randint(0, 127) for _ in range(count)]
        self.y = [random.random() * 128 for _ in range(count)]
        self.speed = [random.random() * 20 + 5 for _ in range(count)]
        self.color = [STAR_COLORS[random.randint(0, 3)] for _ in range(count)]

    @micropython.native
    def update(self, dt):
        for i in range(self.count):
            self.y[i] += self.speed[i] * dt
            if self.y[i] >= 128:
                self.y[i] -= 128
                self.x[i] = random.randint(0, 127)

    @micropython.native
    def draw(self, fb_data):
        buf = memoryview(fb_data)
        for i in range(self.count):
            sx = int(self.x[i])
            sy = int(self.y[i])
            if 0 <= sx < 128 and 0 <= sy < 128:
                offset = (sy * 128 + sx) * 2
                c = self.color[i]
                buf[offset] = c & 0xFF
                buf[offset + 1] = (c >> 8) & 0xFF
