"""Generate retro-style WAV sound effects for Thumbalaga."""
import struct
import math
import random

SAMPLE_RATE = 22050


def write_wav(filename, samples, sample_rate=SAMPLE_RATE, bits=16):
    num_samples = len(samples)
    bytes_per_sample = bits // 8
    data_size = num_samples * bytes_per_sample
    with open(filename, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<IHHIIHH',
            16, 1, 1, sample_rate,
            sample_rate * bytes_per_sample, bytes_per_sample, bits))
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        max_val = (2 ** (bits - 1)) - 1
        for s in samples:
            f.write(struct.pack('<h', int(max(-1.0, min(1.0, s)) * max_val)))


def sine(freq, duration, volume=0.5, decay=True):
    n = int(SAMPLE_RATE * duration)
    return [math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * volume *
            ((1.0 - i / n) if decay else 1.0) for i in range(n)]


def square(freq, duration, volume=0.3, decay=True):
    n = int(SAMPLE_RATE * duration)
    period = SAMPLE_RATE / freq
    return [(volume if (i % int(period)) < (period / 2) else -volume) *
            ((1.0 - i / n) if decay else 1.0) for i in range(n)]


def noise(duration, volume=0.5, decay=True):
    n = int(SAMPLE_RATE * duration)
    return [(random.random() * 2 - 1) * volume *
            ((1.0 - i / n) if decay else 1.0) for i in range(n)]


def sweep(f_start, f_end, duration, volume=0.5, decay=True, wave='sine'):
    """Frequency sweep from f_start to f_end."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f_start + (f_end - f_start) * t
        env = (1.0 - t) if decay else 1.0
        phase += 2 * math.pi * freq / SAMPLE_RATE
        if wave == 'sine':
            samples.append(math.sin(phase) * volume * env)
        else:
            samples.append((1.0 if (phase % (2 * math.pi)) < math.pi else -1.0) * volume * env)
    return samples


def mix(*args):
    length = max(len(a) for a in args)
    result = [0.0] * length
    for a in args:
        for i in range(len(a)):
            result[i] += a[i]
    return result


def concat(*args):
    result = []
    for a in args:
        result.extend(a)
    return result


# ====================================================================
# SHOOT — sharp high-pitched zap
# ====================================================================
shoot = concat(
    sweep(1800, 600, 0.06, 0.5),
)
write_wav('assets/shoot.wav', shoot)
print("shoot.wav")

# ====================================================================
# ENEMY EXPLOSION — crunchy noise burst
# ====================================================================
explode = mix(
    noise(0.18, 0.5),
    sweep(500, 100, 0.15, 0.3),
    sweep(300, 50, 0.12, 0.2),
)
write_wav('assets/explode.wav', explode)
print("explode.wav")

# ====================================================================
# PLAYER DEATH — dramatic descending wail with noise
# ====================================================================
player_die = mix(
    sweep(800, 60, 0.6, 0.5),
    sweep(600, 40, 0.55, 0.3),
    noise(0.6, 0.3),
)
write_wav('assets/player_die.wav', player_die)
print("player_die.wav")

# ====================================================================
# DIVE SOUND — classic swooping descending tone (the iconic Galaga dive)
# Two-tone warbling sweep that descends
# ====================================================================
n = int(SAMPLE_RATE * 0.4)
dive = []
phase1 = 0.0
phase2 = 0.0
for i in range(n):
    t = i / n
    # Main descending sweep
    f1 = 900 - t * 600
    # Warble modulation
    f2 = f1 * 1.02 + math.sin(t * 80) * 50
    env = 0.4 * (1.0 - t * 0.5)
    phase1 += 2 * math.pi * f1 / SAMPLE_RATE
    phase2 += 2 * math.pi * f2 / SAMPLE_RATE
    s = (math.sin(phase1) * 0.5 + math.sin(phase2) * 0.3) * env
    dive.append(s)
write_wav('assets/dive.wav', dive)
print("dive.wav")

# ====================================================================
# TRACTOR BEAM — eerie pulsating hum
# ====================================================================
n = int(SAMPLE_RATE * 1.0)
beam = []
phase = 0.0
for i in range(n):
    t = i / SAMPLE_RATE
    # Low oscillating tone with amplitude modulation
    freq = 120 + math.sin(t * 8) * 30
    phase += 2 * math.pi * freq / SAMPLE_RATE
    amp_mod = 0.5 + 0.5 * math.sin(t * 12)
    env = min(t * 4, 1.0) * 0.4  # fade in
    beam.append(math.sin(phase) * amp_mod * env)
write_wav('assets/beam.wav', beam)
print("beam.wav")

# ====================================================================
# CAPTURE — descending wobble (player caught by beam)
# ====================================================================
capture = mix(
    sweep(600, 200, 0.3, 0.4, wave='square'),
    sweep(550, 180, 0.35, 0.3),
)
# Add wobble
for i in range(len(capture)):
    t = i / SAMPLE_RATE
    capture[i] *= 0.5 + 0.5 * math.sin(t * 25)
write_wav('assets/capture.wav', capture)
print("capture.wav")

# ====================================================================
# TRANSFORM — morphing warble (bee transforms into scorpion etc)
# ====================================================================
transform = concat(
    sweep(200, 800, 0.15, 0.3, decay=False),
    sweep(800, 300, 0.1, 0.3, decay=False),
    sweep(300, 1200, 0.12, 0.4),
)
write_wav('assets/transform.wav', transform)
print("transform.wav")

# ====================================================================
# EXTRA LIFE — cheerful ascending arpeggio
# ====================================================================
extra_life = concat(
    square(523, 0.06, 0.25, False),  # C5
    square(659, 0.06, 0.25, False),  # E5
    square(784, 0.06, 0.25, False),  # G5
    square(1047, 0.12, 0.3),         # C6
)
write_wav('assets/extra_life.wav', extra_life)
print("extra_life.wav")

# ====================================================================
# LEVEL START — stage intro fanfare
# ====================================================================
jingle = concat(
    square(440, 0.08, 0.25, False),
    [0] * int(SAMPLE_RATE * 0.02),
    square(554, 0.08, 0.25, False),
    [0] * int(SAMPLE_RATE * 0.02),
    square(659, 0.08, 0.25, False),
    [0] * int(SAMPLE_RATE * 0.02),
    square(880, 0.18, 0.3),
)
write_wav('assets/level_start.wav', jingle)
print("level_start.wav")

print("\nAll sounds generated!")
