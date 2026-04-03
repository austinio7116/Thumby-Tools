"""Generate 16-bit RGB565 BMP assets for Galaga."""
import struct
import os

def write_bmp_rgb565(filename, width, height, pixels):
    """Write a 16-bit RGB565 BMP file.
    pixels: list of rows, each row is list of RGB565 uint16 values.
    Rows are top-to-bottom in input, but BMP stores bottom-to-top.
    """
    row_size = width * 2
    # Pad each row to 4-byte boundary
    padding = (4 - (row_size % 4)) % 4
    padded_row_size = row_size + padding

    pixel_data_size = padded_row_size * height
    # BMP header: 14 bytes file header + 40 bytes DIB header + 12 bytes masks
    header_size = 14 + 40 + 12
    file_size = header_size + pixel_data_size

    data = bytearray()

    # BMP File Header (14 bytes)
    data += struct.pack('<2sIHHI', b'BM', file_size, 0, 0, header_size)

    # DIB Header (BITMAPINFOHEADER = 40 bytes)
    # For 16-bit with masks, use BI_BITFIELDS compression (3)
    data += struct.pack('<IiiHHIIiiII',
        40,           # header size
        width,        # width
        height,       # height (positive = bottom-up, standard BMP)
        1,            # planes
        16,           # bits per pixel
        3,            # compression = BI_BITFIELDS
        pixel_data_size,  # image size
        0, 0,         # resolution
        0, 0          # colors
    )

    # Color masks for RGB565
    data += struct.pack('<III',
        0xF800,   # red mask
        0x07E0,   # green mask
        0x001F    # blue mask
    )

    # Pixel data (bottom-up: reverse row order for standard BMP)
    for row in reversed(pixels):
        for pixel in row:
            data += struct.pack('<H', pixel & 0xFFFF)
        data += b'\x00' * padding

    with open(filename, 'wb') as f:
        f.write(data)


def rgb(r, g, b):
    """Convert 8-bit RGB to RGB565."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# Transparent color
T = 0xF81F  # magenta

# ============================================================
# PLAYER SHIP (12x12) - Classic arrow/fighter shape
# ============================================================
C = rgb(0, 255, 255)    # cyan body
W = rgb(255, 255, 255)  # white highlights
B = rgb(0, 128, 255)    # blue accent
D = rgb(0, 80, 160)     # dark blue
R = rgb(255, 60, 60)    # red engine

player_pixels = [
    [T,T,T,T,T,W,W,T,T,T,T,T],
    [T,T,T,T,T,W,W,T,T,T,T,T],
    [T,T,T,T,C,W,W,C,T,T,T,T],
    [T,T,T,T,C,C,C,C,T,T,T,T],
    [T,T,T,C,C,C,C,C,C,T,T,T],
    [T,T,T,C,B,C,C,B,C,T,T,T],
    [T,T,C,C,B,C,C,B,C,C,T,T],
    [T,C,C,C,B,C,C,B,C,C,C,T],
    [T,C,D,C,C,C,C,C,C,D,C,T],
    [C,C,D,C,C,C,C,C,C,D,C,C],
    [C,D,D,R,C,C,C,C,R,D,D,C],
    [T,T,T,R,T,R,R,T,R,T,T,T],
]

write_bmp_rgb565('assets/player.bmp', 12, 12, player_pixels)
print("Created player.bmp (12x12)")

# ============================================================
# ENEMIES SPRITE SHEET (8x24) - 3 rows of 8x8
# Row 0: Bee (yellow), Row 1: Butterfly (purple/pink), Row 2: Boss (green)
# ============================================================
# Bee colors
Y = rgb(255, 220, 0)    # yellow
O = rgb(200, 140, 0)    # dark yellow/orange

bee = [
    [T,T,T,Y,Y,T,T,T],
    [T,T,Y,Y,Y,Y,T,T],
    [T,Y,O,Y,Y,O,Y,T],
    [T,Y,Y,Y,Y,Y,Y,T],
    [Y,T,Y,Y,Y,Y,T,Y],
    [Y,T,T,Y,Y,T,T,Y],
    [T,T,Y,T,T,Y,T,T],
    [T,T,T,T,T,T,T,T],
]

# Butterfly colors
P = rgb(200, 50, 200)   # purple
K = rgb(255, 100, 255)  # pink
BL = rgb(100, 50, 200)  # blue-purple

butterfly = [
    [T,T,T,K,K,T,T,T],
    [T,T,K,P,P,K,T,T],
    [T,K,P,K,K,P,K,T],
    [K,P,P,P,P,P,P,K],
    [K,BL,P,P,P,P,BL,K],
    [T,K,T,P,P,T,K,T],
    [T,T,K,T,T,K,T,T],
    [T,K,T,T,T,T,K,T],
]

# Boss Galaga colors
G = rgb(0, 200, 100)    # green
DG = rgb(0, 140, 60)    # dark green
LG = rgb(100, 255, 150) # light green
RD = rgb(255, 50, 50)   # red eye

boss = [
    [T,T,DG,G,G,DG,T,T],
    [T,DG,G,LG,LG,G,DG,T],
    [T,G,RD,G,G,RD,G,T],
    [DG,G,G,G,G,G,G,DG],
    [G,G,LG,G,G,LG,G,G],
    [G,DG,G,G,G,G,DG,G],
    [T,G,DG,G,G,DG,G,T],
    [T,T,G,T,T,G,T,T],
]

enemies_pixels = bee + butterfly + boss
write_bmp_rgb565('assets/enemies.bmp', 8, 24, enemies_pixels)
print("Created enemies.bmp (8x24, 3 enemy types)")

# ============================================================
# EXPLOSION SPRITE SHEET (32x8) - 4 frames of 8x8
# ============================================================
WH = rgb(255, 255, 255)
YL = rgb(255, 200, 0)
OR = rgb(255, 120, 0)
RR = rgb(255, 40, 0)

# Frame 1: small burst
f1 = [
    [T, T, T, T, T, T, T, T],
    [T, T, T, T, T, T, T, T],
    [T, T, T, WH,WH,T, T, T],
    [T, T, WH,YL,YL,WH,T, T],
    [T, T, WH,YL,YL,WH,T, T],
    [T, T, T, WH,WH,T, T, T],
    [T, T, T, T, T, T, T, T],
    [T, T, T, T, T, T, T, T],
]

# Frame 2: medium burst
f2 = [
    [T, T, T, T, T, T, T, T],
    [T, T, WH,T, T, WH,T, T],
    [T, WH,YL,YL,YL,YL,WH,T],
    [T, T, YL,WH,WH,YL,T, T],
    [T, T, YL,WH,WH,YL,T, T],
    [T, WH,YL,YL,YL,YL,WH,T],
    [T, T, WH,T, T, WH,T, T],
    [T, T, T, T, T, T, T, T],
]

# Frame 3: large burst
f3 = [
    [T, T, OR,T, T, OR,T, T],
    [T, OR,YL,WH,WH,YL,OR,T],
    [OR,YL,WH,YL,YL,WH,YL,OR],
    [T, WH,YL,OR,OR,YL,WH,T],
    [T, WH,YL,OR,OR,YL,WH,T],
    [OR,YL,WH,YL,YL,WH,YL,OR],
    [T, OR,YL,WH,WH,YL,OR,T],
    [T, T, OR,T, T, OR,T, T],
]

# Frame 4: dissipating
f4 = [
    [T, T, T, RR,T, T, T, T],
    [T, RR,T, T, T, T, OR,T],
    [T, T, T, OR,T, T, T, T],
    [RR,T, OR,T, T, RR,T, T],
    [T, T, T, T, T, T, T, RR],
    [T, T, T, RR,T, T, T, T],
    [T, OR,T, T, T, OR,T, T],
    [T, T, T, T, RR,T, T, T],
]

# Combine frames side by side (32x8)
explosion_pixels = []
for row_idx in range(8):
    explosion_pixels.append(f1[row_idx] + f2[row_idx] + f3[row_idx] + f4[row_idx])

write_bmp_rgb565('assets/explosion.bmp', 32, 8, explosion_pixels)
print("Created explosion.bmp (32x8, 4 frames)")

# ============================================================
# PLAYER EXPLOSION (12x12) - single frame, bigger and different color
# ============================================================
player_exp = [
    [T, T, WH,T, T, T, T, T, T, WH,T, T],
    [T, WH,T, T, T, WH,T, T, T, T, WH,T],
    [WH,T, T, YL,T, T, T, T, YL,T, T, WH],
    [T, T, YL,WH,YL,T, T, YL,WH,YL,T, T],
    [T, T, T, YL,WH,YL,YL,WH,YL,T, T, T],
    [T, WH,T, T, YL,WH,WH,YL,T, T, WH,T],
    [T, T, T, T, YL,WH,WH,YL,T, T, T, T],
    [T, T, T, YL,WH,YL,YL,WH,YL,T, T, T],
    [T, T, YL,WH,YL,T, T, YL,WH,YL,T, T],
    [WH,T, T, YL,T, T, T, T, YL,T, T, WH],
    [T, WH,T, T, T, T, WH,T, T, T, WH,T],
    [T, T, WH,T, T, T, T, T, T, WH,T, T],
]

write_bmp_rgb565('assets/player_explosion.bmp', 12, 12, player_exp)
print("Created player_explosion.bmp (12x12)")

# ============================================================
# SMALL LIFE ICON (6x6) - tiny player ship for lives display
# ============================================================
life_icon = [
    [T, T, C, C, T, T],
    [T, C, C, C, C, T],
    [T, C, B, B, C, T],
    [C, C, C, C, C, C],
    [C, D, C, C, D, C],
    [T, T, R, R, T, T],
]

write_bmp_rgb565('assets/life_icon.bmp', 6, 6, life_icon)
print("Created life_icon.bmp (6x6)")

print("\nAll assets generated successfully!")
