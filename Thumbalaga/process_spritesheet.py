"""Process Galaga spritesheet into 12x12 RGB565 BMPs with all enemy types.

Enemy sheet: 8 frames x 8 types (bee, butterfly, boss, boss_hit,
             scorpion, bosconian, galaxian, dragonfly)
Tractor beam: 3 animation frames scaled to 12x20
"""

import struct
from PIL import Image

SRC = '/tmp/Arcade - Galaga - Miscellaneous - General Sprites.png'
OUT = '/home/maustin/thumby-color/Thumbalaga/assets'
BG = (64, 64, 64)
S = 12  # sprite size


def rgb888_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

MAGENTA_565 = rgb888_to_rgb565(255, 0, 255)


def write_bmp_rgb565(filename, width, height, pixel_data_565):
    row_size = width * 2
    padding = (4 - (row_size % 4)) % 4
    padded_row_size = row_size + padding
    pixel_data_size = padded_row_size * height
    header_size = 14 + 40 + 12
    file_size = header_size + pixel_data_size
    data = bytearray()
    data += struct.pack('<2sIHHI', b'BM', file_size, 0, 0, header_size)
    data += struct.pack('<IiiHHIIiiII',
        40, width, height, 1, 16, 3, pixel_data_size, 0, 0, 0, 0)
    data += struct.pack('<III', 0xF800, 0x07E0, 0x001F)
    for row in range(height - 1, -1, -1):
        for col in range(width):
            px = pixel_data_565[row * width + col]
            data += struct.pack('<H', px & 0xFFFF)
        data += b'\x00' * padding
    with open(filename, 'wb') as f:
        f.write(data)


def convert_pixel(r, g, b, a):
    if (r, g, b) == BG or (r, g, b) == (0, 0, 0) or a == 0:
        return MAGENTA_565
    return rgb888_to_rgb565(r, g, b)


def extract_and_scale(img, x, y, src_w, src_h, dst_w, dst_h):
    cell = img.crop((x, y, x + src_w, y + src_h))
    scaled = cell.resize((dst_w, dst_h), Image.NEAREST)
    return [convert_pixel(*scaled.getpixel((px, py)))
            for py in range(dst_h) for px in range(dst_w)]


def s1(col, row):
    return (1 + col * 18, 1 + row * 18)


def make_strip_row(img, src_row, num_cols):
    """Extract a row of sprites as a horizontal strip, scaled to SxS."""
    pixels = []
    for py in range(S):
        for col in range(num_cols):
            x, y = s1(col, src_row)
            cell = img.crop((x, y, x + 16, y + 16))
            scaled = cell.resize((S, S), Image.NEAREST)
            for px in range(S):
                pixels.append(convert_pixel(*scaled.getpixel((px, py))))
    return pixels


def preview(name, w, h, data):
    pimg = Image.new('RGBA', (w, h))
    for py in range(h):
        for px in range(w):
            v = data[py * w + px]
            if v == MAGENTA_565:
                pimg.putpixel((px, py), (255, 0, 255, 0))
            else:
                r = ((v >> 11) & 0x1F) << 3
                g = ((v >> 5) & 0x3F) << 2
                b = (v & 0x1F) << 3
                pimg.putpixel((px, py), (r, g, b, 255))
    big = pimg.resize((w * 4, h * 4), Image.NEAREST)
    big.save(f"/tmp/preview_{name}.png")


# ====================================================================
img = Image.open(SRC).convert('RGBA')
print(f"Loaded: {img.size}")

# ====================================================================
# PLAYER SHIP — Row 0, col 6 (facing down)
# ====================================================================
px, py = s1(6, 0)
player_px = extract_and_scale(img, px, py, 16, 16, S, S)
write_bmp_rgb565(f"{OUT}/player.bmp", S, S, player_px)
write_bmp_rgb565(f"{OUT}/life_icon.bmp", S, S, player_px)
preview("player", S, S, player_px)
print("player.bmp + life_icon.bmp")

# ====================================================================
# ENEMIES — 8 frames x 10 types
# Row order matches constants: BEE=0, BUTTERFLY=1, BOSS=2, BOSS_HIT=3,
#   SCORPION=4, BOSCONIAN=5, GALAXIAN=6, DRAGONFLY=7, SATELLITE=8, ENTERPRISE=9
# Source: S1 rows 4,5,2,3,6,7,8,9 + S2 rows 0,1
# ====================================================================
FRAMES = 8

# Section 2 sprite position helper (x=145+, 18px grid, y starts at 37)
def s2(col, row):
    return (145 + col * 18, 37 + row * 18)

# Complete sprite sheet: 20 rows x 8 frames
# Normal sprites (rows 0-9):
#   0=Bee, 1=Butterfly, 2=Boss, 3=BossHit,
#   4=Scorpion, 5=Bosconian, 6=Galaxian,
#   7=Dragonfly, 8=Satellite, 9=Enterprise
# Hit/dying palette (rows 10-18):
#   10=Boss dying, 11=Bee dying, 12=Butterfly dying,
#   13=Scorpion dying, 14=Bosconian dying, 15=Galaxian dying,
#   16=Dragonfly dying, 17=Enterprise dying, 18=Satellite dying
# Pre-transform pulsating (row 19)

sprite_defs = [
    # Normal sprites from Section 1
    # S1 Row 5 = Bee/Zako (blue/yellow), S1 Row 4 = Butterfly/Goei (red/white)
    (s1, 5, 8, "Bee"),
    (s1, 4, 8, "Butterfly"),
    (s1, 2, 8, "Boss"),
    (s1, 3, 8, "BossHit"),
    (s1, 6, 7, "Scorpion"),
    (s1, 7, 7, "Bosconian"),
    (s1, 8, 7, "Galaxian"),
    (s1, 9, 7, "Dragonfly"),
    (s1, 10, 6, "Satellite"),
    (s1, 11, 7, "Enterprise"),
    # Hit/dying palette from Section 2
    # S2 Row 0 = Boss dying, Row 2 = Bee dying (matches S1 R5), Row 1 = Butterfly dying (matches S1 R4)
    (s2, 0, 8, "Boss dying"),
    (s2, 2, 8, "Bee dying"),
    (s2, 1, 8, "Butterfly dying"),
    (s2, 3, 7, "Scorpion dying"),
    (s2, 4, 7, "Bosconian dying"),
    (s2, 5, 7, "Galaxian dying"),
    (s2, 6, 7, "Dragonfly dying"),
    (s2, 7, 7, "Enterprise dying"),
    (s2, 8, 6, "Satellite dying"),
    # Pre-transform pulsating
    (s2, 9, 6, "Pre-transform"),
]

sheet_w = FRAMES * S  # 96
sheet_h = len(sprite_defs) * S  # 240

enemy_pixels = []
for src_fn, src_row, ncols, name in sprite_defs:
    for py_idx in range(S):
        for col in range(FRAMES):
            actual_col = min(col, ncols - 1)
            x, y = src_fn(actual_col, src_row)
            cell = img.crop((x, y, x + 16, y + 16))
            scaled = cell.resize((S, S), Image.NEAREST)
            for px_idx in range(S):
                enemy_pixels.append(convert_pixel(*scaled.getpixel((px_idx, py_idx))))
    print(f"  {name}: row {src_row}, {ncols} frames")

write_bmp_rgb565(f"{OUT}/enemies.bmp", sheet_w, sheet_h, enemy_pixels)
preview("enemies", sheet_w, sheet_h, enemy_pixels)
print(f"enemies.bmp ({sheet_w}x{sheet_h}) — {FRAMES} frames x {len(sprite_defs)} types")

# ====================================================================
# ENEMY EXPLOSIONS — 5 frames from section 3 top (32x32 each, scaled to 12x12)
# ====================================================================
exp_positions = [(289, 1), (323, 1), (357, 1), (391, 1), (425, 1)]
exp_strip = []
for py_idx in range(S):
    for ex, ey in exp_positions:
        cell = img.crop((ex, ey, ex + 32, ey + 32))
        scaled = cell.resize((S, S), Image.NEAREST)
        for px_idx in range(S):
            exp_strip.append(convert_pixel(*scaled.getpixel((px_idx, py_idx))))

exp_w = S * len(exp_positions)
write_bmp_rgb565(f"{OUT}/explosion.bmp", exp_w, S, exp_strip)
preview("explosion", exp_w, S, exp_strip)
print(f"explosion.bmp ({exp_w}x{S}) — 5 enemy explosion frames")

# ====================================================================
# PLAYER EXPLOSION — 4 frames from section 2 top (white/red, 32x32 scaled to 12x12)
# ====================================================================
pexp_positions = [(145, 1), (179, 1), (213, 1), (247, 1)]
pexp_strip = []
for py_idx in range(S):
    for ex, ey in pexp_positions:
        cell = img.crop((ex, ey, ex + 32, ey + 32))
        scaled = cell.resize((S, S), Image.NEAREST)
        for px_idx in range(S):
            pexp_strip.append(convert_pixel(*scaled.getpixel((px_idx, py_idx))))

pexp_w = S * len(pexp_positions)
write_bmp_rgb565(f"{OUT}/player_explosion.bmp", pexp_w, S, pexp_strip)
preview("player_explosion", pexp_w, S, pexp_strip)
print(f"player_explosion.bmp ({pexp_w}x{S}) — 4 player explosion frames")

# ====================================================================
# TRACTOR BEAM — 3 frames at section 3 (x=289, y=36), each 48x80
# Scale to 12x20, horizontal strip: 36x20
# ====================================================================
BEAM_W = 16
BEAM_H = 28
beam_positions = [(289, 36), (339, 36), (389, 36)]
beam_strip = []
for py_idx in range(BEAM_H):
    for bx, by in beam_positions:
        cell = img.crop((bx, by, bx + 48, by + 80))
        scaled = cell.resize((BEAM_W, BEAM_H), Image.NEAREST)
        for px_idx in range(BEAM_W):
            beam_strip.append(convert_pixel(*scaled.getpixel((px_idx, py_idx))))

beam_total_w = BEAM_W * len(beam_positions)
write_bmp_rgb565(f"{OUT}/tractor_beam.bmp", beam_total_w, BEAM_H, beam_strip)
preview("tractor_beam", beam_total_w, BEAM_H, beam_strip)
print(f"tractor_beam.bmp ({beam_total_w}x{BEAM_H}) — 3 frames")

print("\n=== DONE ===")
