from constants import *


@micropython.native
def check_player_bullets_vs_enemies(bullets, formation):
    """Check player bullets against all enemies. Returns list of (bullet_idx, enemy)."""
    hits = []
    enemies = formation.enemies
    num_enemies = FORM_COLS * FORM_ROWS

    for bi in range(MAX_PLAYER_BULLETS):
        if not bullets.p_active[bi]:
            continue
        bx = bullets.p_x[bi]
        by = bullets.p_y[bi]

        for ei in range(num_enemies):
            e = enemies[ei]
            if e is None or not e.alive:
                continue
            if e.node.opacity < 0.5:
                continue

            ex = e.node.position.x
            ey = e.node.position.y

            # AABB overlap test
            if (abs(bx - ex) < ENEMY_HALF + 1 and
                abs(by - ey) < ENEMY_HALF + 2):
                hits.append((bi, e))
                break  # bullet can only hit one enemy

    return hits


@micropython.native
def check_enemy_bullets_vs_player(bullets, player):
    """Check enemy bullets against player. Returns index of hitting bullet or -1."""
    if not player.alive or player.is_invincible():
        return -1

    px = player.position.x
    py = player.position.y

    for i in range(MAX_ENEMY_BULLETS):
        if not bullets.e_active[i]:
            continue
        bx = bullets.e_x[i]
        by = bullets.e_y[i]

        if (abs(bx - px) < PLAYER_HALF_W and
            abs(by - py) < PLAYER_HALF_H):
            return i

    return -1


@micropython.native
def check_divers_vs_player(formation, player):
    """Check diving enemies against player. Returns hitting enemy or None."""
    if not player.alive or player.is_invincible():
        return None

    px = player.position.x
    py = player.position.y

    for e in formation.enemies:
        if e is None or not e.alive or e.in_formation or not e.entry_done:
            continue
        ex = e.node.position.x
        ey = e.node.position.y

        if (abs(ex - px) < ENEMY_HALF + PLAYER_HALF_W - 2 and
            abs(ey - py) < ENEMY_HALF + PLAYER_HALF_H - 2):
            return e

    return None
