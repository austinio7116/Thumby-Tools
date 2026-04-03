# Screen
SCREEN_W = const(128)
SCREEN_H = const(128)

# Formation grid
FORM_COLS = const(8)
FORM_ROWS = const(5)
FORM_SPACING_X = const(14)
FORM_SPACING_Y = const(13)
# Formation top-left origin (camera coords: -64 to +64)
FORM_ORIGIN_X = -42           # left edge of formation
FORM_ORIGIN_Y = -46           # top row, below HUD area

# Enemy types (match sprite sheet row order in enemies.bmp)
ENEMY_BEE = const(0)
ENEMY_BUTTERFLY = const(1)
ENEMY_BOSS = const(2)
ENEMY_BOSS_HIT = const(3)
ENEMY_SCORPION = const(4)
ENEMY_BOSCONIAN = const(5)
ENEMY_GALAXIAN = const(6)
ENEMY_DRAGONFLY = const(7)
ENEMY_SATELLITE = const(8)
ENEMY_ENTERPRISE = const(9)
# Hit/dying palette versions (brief flash before explosion)
ENEMY_BOSS_DYING = const(10)
ENEMY_BEE_DYING = const(11)
ENEMY_BUTTERFLY_DYING = const(12)
ENEMY_SCORPION_DYING = const(13)
ENEMY_BOSCONIAN_DYING = const(14)
ENEMY_GALAXIAN_DYING = const(15)
ENEMY_DRAGONFLY_DYING = const(16)
ENEMY_ENTERPRISE_DYING = const(17)
ENEMY_SATELLITE_DYING = const(18)
ENEMY_PRETRANSFORM = const(19)  # pulsating bee before morphing
NUM_ENEMY_TYPES = const(20)

# Hostile captured fighter — uses player_captured (red) sprite, not in enemy sheet
HOSTILE_FIGHTER_POINTS = const(1000)

# Points: (in_formation, diving)
POINTS_BEE = (50, 100)
POINTS_BUTTERFLY = (80, 160)
POINTS_BOSS = (150, 400)
POINTS_TRANSFORM = (150, 300)  # scorpion, bosconian, galaxian, dragonfly
POINTS_CHALLENGE = (100, 100)  # challenge-exclusive enemies
POINTS = (POINTS_BEE, POINTS_BUTTERFLY, POINTS_BOSS, POINTS_BOSS,
          POINTS_TRANSFORM, POINTS_TRANSFORM, POINTS_TRANSFORM, POINTS_TRANSFORM,
          POINTS_CHALLENGE, POINTS_CHALLENGE,
          POINTS_BOSS, POINTS_BEE, POINTS_BUTTERFLY,  # dying versions (same pts)
          POINTS_TRANSFORM, POINTS_TRANSFORM, POINTS_TRANSFORM,
          POINTS_CHALLENGE, POINTS_CHALLENGE, POINTS_CHALLENGE,
          POINTS_BEE)  # pretransform

# Enemy HP by type
ENEMY_HP = (1, 1, 2, 1, 1, 1, 2, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1)

# Map normal enemy type to its dying palette version
DYING_PALETTE = {
    ENEMY_BEE: ENEMY_BEE_DYING,
    ENEMY_BUTTERFLY: ENEMY_BUTTERFLY_DYING,
    ENEMY_BOSS: ENEMY_BOSS_DYING,
    ENEMY_BOSS_HIT: ENEMY_BOSS_DYING,
    ENEMY_SCORPION: ENEMY_SCORPION_DYING,
    ENEMY_BOSCONIAN: ENEMY_BOSCONIAN_DYING,
    ENEMY_GALAXIAN: ENEMY_GALAXIAN_DYING,
    ENEMY_DRAGONFLY: ENEMY_DRAGONFLY_DYING,
    ENEMY_SATELLITE: ENEMY_SATELLITE_DYING,
    ENEMY_ENTERPRISE: ENEMY_ENTERPRISE_DYING,
}

# Transform enemy appearance by stage range
# (min_stage, enemy_type) — which transform enemy appears
TRANSFORM_STAGES = (
    (4, ENEMY_SCORPION),
    (8, ENEMY_BOSCONIAN),
    (12, ENEMY_GALAXIAN),
    (16, ENEMY_DRAGONFLY),
)

# Tractor beam
BEAM_DURATION = 3.0       # seconds the beam is active
BEAM_DIVE_SPEED = 0.3     # boss dive speed during beam
BEAM_WIDTH = const(16)    # scaled beam width
BEAM_HEIGHT = const(28)   # scaled beam height
BEAM_FPS = const(6)       # beam animation speed

# Player (camera coords: -64 to +64)
PLAYER_Y = 51                # near bottom of screen (64 - 13)
PLAYER_SPEED = 80.0          # pixels/sec
PLAYER_START_X = 0            # center of screen

# Bullets
MAX_PLAYER_BULLETS = const(4)  # 2 normally, need 4 for dual fighter
MAX_ENEMY_BULLETS = const(8)
PLAYER_BULLET_SPEED = 150.0
ENEMY_BULLET_SPEED = 60.0
BULLET_W = const(2)
PLAYER_BULLET_H = const(4)
ENEMY_BULLET_H = const(3)

# Collision half-sizes (12x12 sprites)
ENEMY_HALF = const(5)        # 12x12 sprite, slightly tight hitbox
PLAYER_HALF_W = const(5)
PLAYER_HALF_H = const(5)

# Enemy sprite frames (frame 0 = facing left, frame 7 = facing down)
ENEMY_FRAMES = const(8)      # max rotation frames per enemy type
IDLE_FRAME_A = const(6)       # facing-down frame 1 (for 8-frame enemies)
IDLE_FRAME_B = const(7)       # facing-down frame 2 (for 8-frame enemies)
IDLE_ANIM_FPS = 3.0           # idle wing-flap speed (frames per second)

# Per-type frame count (some enemies have fewer rotation frames)
ENEMY_FRAME_COUNT = (8, 8, 8, 8, 7, 7, 7, 7, 6, 7,  # normal types
                     8, 8, 8, 7, 7, 7, 7, 7, 6, 6)   # dying + pretransform

# Per-type idle frames (the two "facing down" frames for animation)
def get_idle_frames(etype):
    fc = ENEMY_FRAME_COUNT[etype] if etype < len(ENEMY_FRAME_COUNT) else 8
    if fc >= 8:
        return 6, 7
    elif fc >= 6:
        return fc - 2, fc - 1  # last two frames
    else:
        return 0, 1

# Colors (RGB565)
COL_BLACK = const(0x0000)
COL_WHITE = const(0xFFFF)
COL_YELLOW = const(0xFFE0)
COL_RED = const(0xF800)
COL_CYAN = const(0x07FF)
COL_GREEN = const(0x07E0)
COL_MAGENTA = const(0xF81F)  # transparent color
COL_ORANGE = const(0xFD20)
COL_DARK_GREY = const(0x4208)
COL_MID_GREY = const(0x6B4D)
COL_LIGHT_GREY = const(0x9CF3)

# Star colors for parallax layers
STAR_COLORS = (COL_DARK_GREY, COL_MID_GREY, COL_LIGHT_GREY, COL_WHITE)

# Audio channels
CH_SHOOT = const(0)
CH_EXPLODE = const(1)
CH_PLAYER_DIE = const(2)
CH_MUSIC = const(3)

# Game states
ST_TITLE = const(0)
ST_STAGE_INTRO = const(1)
ST_ENTRY = const(2)
ST_PLAYING = const(3)
ST_DYING = const(4)
ST_STAGE_CLEAR = const(5)
ST_GAME_OVER = const(6)
ST_CHALLENGE = const(7)

# Formation sway
SWAY_SPEED = 10.0
SWAY_RANGE = 6.0

# Dive attack
DIVE_SPEED_BASE = 0.4
ENTRY_DURATION = 1.2  # seconds for entry path traversal
ENTRY_LERP_DURATION = 0.4  # seconds to lerp from path end to formation slot

# Explosion
MAX_EXPLOSIONS = const(4)
EXPLOSION_FPS = const(10)
EXPLOSION_FRAMES = const(5)  # 5 frames from section 3 of spritesheet

# Lives
START_LIVES = const(3)
