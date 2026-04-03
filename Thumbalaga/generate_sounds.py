"""Generate simple retro WAV sound effects for Galaga."""
import struct
import math

SAMPLE_RATE = 22050


def write_wav(filename, samples, sample_rate=SAMPLE_RATE, bits=16):
    """Write a WAV file from a list of float samples (-1.0 to 1.0)."""
    num_samples = len(samples)
    bytes_per_sample = bits // 8
    data_size = num_samples * bytes_per_sample

    with open(filename, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')

        # fmt chunk
        f.write(b'fmt ')
        f.write(struct.pack('<IHHIIHH',
            16,             # chunk size
            1,              # PCM format
            1,              # mono
            sample_rate,
            sample_rate * bytes_per_sample,
            bytes_per_sample,
            bits
        ))

        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))

        max_val = (2 ** (bits - 1)) - 1
        for s in samples:
            s = max(-1.0, min(1.0, s))
            f.write(struct.pack('<h', int(s * max_val)))


def sine(freq, duration, volume=0.5, decay=True):
    """Generate sine wave samples."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = 1.0 - (t / duration) if decay else 1.0
        samples.append(math.sin(2 * math.pi * freq * t) * volume * env)
    return samples


def square(freq, duration, volume=0.3, decay=True):
    """Generate square wave samples."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    period = SAMPLE_RATE / freq
    for i in range(n):
        t = i / SAMPLE_RATE
        env = 1.0 - (t / duration) if decay else 1.0
        val = volume if (i % int(period)) < (period / 2) else -volume
        samples.append(val * env)
    return samples


def noise(duration, volume=0.5, decay=True):
    """Generate white noise samples."""
    import random
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = 1.0 - (t / duration) if decay else 1.0
        samples.append((random.random() * 2 - 1) * volume * env)
    return samples


def mix(a, b):
    """Mix two sample lists together."""
    length = max(len(a), len(b))
    result = []
    for i in range(length):
        va = a[i] if i < len(a) else 0
        vb = b[i] if i < len(b) else 0
        result.append(va + vb)
    return result


# ── Shoot SFX ──
# Short high-pitched blip
shoot = sine(1200, 0.04, 0.4) + sine(800, 0.03, 0.3)
write_wav('assets/shoot.wav', shoot)
print("Created shoot.wav")

# ── Enemy Explosion SFX ──
# Noise burst with frequency sweep down
explode = mix(
    noise(0.15, 0.4),
    sine(400, 0.1, 0.3) + sine(200, 0.08, 0.2)
)
write_wav('assets/explode.wav', explode)
print("Created explode.wav")

# ── Player Death SFX ──
# Longer, descending tone with noise
die_tone = []
n = int(SAMPLE_RATE * 0.5)
for i in range(n):
    t = i / SAMPLE_RATE
    freq = 600 - t * 800  # sweep down
    if freq < 80:
        freq = 80
    env = 1.0 - (t / 0.5)
    die_tone.append(math.sin(2 * math.pi * freq * t) * 0.4 * env)

die_noise = noise(0.5, 0.25)
player_die = mix(die_tone, die_noise)
write_wav('assets/player_die.wav', player_die)
print("Created player_die.wav")

# ── Level Start Jingle ──
# Short ascending arpeggio
jingle = (
    square(440, 0.08, 0.25, False) +
    square(554, 0.08, 0.25, False) +
    square(659, 0.08, 0.25, False) +
    square(880, 0.15, 0.3)
)
write_wav('assets/level_start.wav', jingle)
print("Created level_start.wav")

print("\nAll sounds generated!")
