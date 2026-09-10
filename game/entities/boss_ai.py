"""AI for the Slime King boss: three health-ratio phases, each adding a
distinct attack on top of the previous one's. Mirrors enemy_ai.py's shape
(a pure function over (boss, world, player, dt)), but Boss instances live
in GameApp's shared `enemies` list alongside regular enemies, and Boss
itself has no access to the projectile/enemies lists it needs to spawn
into -- so, like combat_system.try_attack returning a new Projectile
instead of appending to one, `update` returns what it spawned (any
EnemyProjectiles fired this tick, a list of minion Enemy instances) for
GameApp to actually add. See GameApp.step, which calls this in its own
loop (bosses are skipped by the regular enemy_ai.update loop).

Phase 1 (ratio > BOSS_PHASE_2_HEALTH_RATIO): hops toward the player,
contact damage, AND already lobs a gravity-arced Slime Lob projectile at
the player on a cooldown from the very start of the fight -- ranged
attacks used to only unlock at phase 2 (<=66% health), but that meant a
player who never brought the boss that low (or died/fled first) could
go a whole fight without ever seeing a projectile, which is exactly what
"crie projéteis" asked for. Its hop leads the player's velocity to
predict where they'll actually land instead of aiming at where they
started the hop (see _update_hop_movement), and steps over a 1-tile
bump in its flight path instead of stalling against it the way a plain
move_axis collision would (see _step_over_ledge).
Phase 2 (<= BOSS_PHASE_2_HEALTH_RATIO): hops and lobs faster.
Phase 3 (<= BOSS_PHASE_3_HEALTH_RATIO): enrages once (summons
SLIME_KING_MINION_COUNT regular Slimes), hops/lobs faster still, the lob
becomes a SLIME_KING_SPREAD_COUNT-projectile fan instead of a single
shot, and every landing triggers a radius shockwave (stomp_pending --
see combat_system.resolve_boss_stomp) that can hit the player without a
direct hitbox overlap.
"""
import math
import random
from typing import List, Optional, Tuple

from game.entities import tile_collision
from game.entities import enemy_registry
from game.entities.boss import Boss
from game.entities.enemy import Enemy
from game.combat.enemy_projectile import EnemyProjectile
from game.settings import (
    GRAVITY, MAX_FALL_SPEED, TILE_SIZE,
    BOSS_PHASE_2_HEALTH_RATIO, BOSS_PHASE_3_HEALTH_RATIO,
    SLIME_KING_HOP_IMPULSE, SLIME_KING_HOP_INTERVAL_MIN_S, SLIME_KING_HOP_INTERVAL_MAX_S,
    SLIME_KING_HOP_LEAD_SPEED_MULT,
    SLIME_KING_PHASE_SPEED_MULT, SLIME_KING_LOB_DAMAGE, SLIME_KING_LOB_COOLDOWN_S,
    SLIME_KING_LOB_SPEED, SLIME_KING_SPREAD_COUNT, SLIME_KING_SPREAD_ANGLE_DEGREES,
    SLIME_KING_MINION_COUNT,
)
from game.world.world import World

SLIME_MINION_ID = "slime"


def _phase_for_ratio(ratio: float) -> int:
    if ratio <= BOSS_PHASE_3_HEALTH_RATIO:
        return 2
    if ratio <= BOSS_PHASE_2_HEALTH_RATIO:
        return 1
    return 0


def update(boss: Boss, world: World, player, dt: float) -> Tuple[List[EnemyProjectile], List[Enemy]]:
    boss.invulnerability_remaining = max(0.0, boss.invulnerability_remaining - dt)
    boss.stomp_pending = False
    if not boss.alive:
        return [], []

    ratio = boss.health / boss.enemy_def.max_health
    new_phase = _phase_for_ratio(ratio)
    minions: List[Enemy] = []
    if new_phase > boss.phase_index:
        boss.phase_index = new_phase
        if new_phase == 2 and not boss.enraged:
            boss.enraged = True
            minions = _spawn_minions(boss)

    was_on_ground = boss.on_ground
    _update_hop_movement(boss, world, player, dt)
    if boss.on_ground and not was_on_ground and boss.phase_index == 2:
        boss.stomp_pending = True

    projectiles: List[EnemyProjectile] = []
    boss.ranged_cooldown_remaining -= dt
    if boss.ranged_cooldown_remaining <= 0.0:
        projectiles = _fire_projectiles(boss, player)
        boss.ranged_cooldown_remaining = SLIME_KING_LOB_COOLDOWN_S / SLIME_KING_PHASE_SPEED_MULT[boss.phase_index]

    return projectiles, minions


def _spawn_minions(boss: Boss) -> List[Enemy]:
    minion_def = enemy_registry.get(SLIME_MINION_ID)
    minions = []
    for i in range(SLIME_KING_MINION_COUNT):
        offset = (i // 2 + 1) * TILE_SIZE * (1 if i % 2 == 0 else -1)
        minions.append(Enemy(minion_def, boss.center_x + offset, boss.y))
    return minions


def _update_hop_movement(boss: Boss, world: World, player, dt: float) -> None:
    speed_mult = SLIME_KING_PHASE_SPEED_MULT[boss.phase_index]
    boss.y_vel = min(boss.y_vel + GRAVITY, MAX_FALL_SPEED)

    if boss.on_ground and boss.invulnerability_remaining <= 0.0:
        boss.hop_cooldown_remaining -= dt
        if boss.hop_cooldown_remaining <= 0.0:
            hop_impulse = SLIME_KING_HOP_IMPULSE * min(1.15, speed_mult)
            # Symmetric parabola (launches and lands at the same height):
            # time to peak is impulse/GRAVITY, so total flight is double
            # that -- in frames, since neither GRAVITY nor x_vel/y_vel are
            # dt-scaled here (this engine's physics is frame-based, see
            # the "px/frame" convention noted at the top of settings.py).
            flight_frames = max(1.0, 2.0 * hop_impulse / GRAVITY)
            predicted_x = player.center_x + player.x_vel * flight_frames
            dx = predicted_x - boss.center_x
            desired_speed = dx / flight_frames
            max_speed = boss.enemy_def.move_speed * speed_mult * SLIME_KING_HOP_LEAD_SPEED_MULT
            speed = max(-max_speed, min(max_speed, desired_speed))
            min_speed = boss.enemy_def.move_speed * speed_mult * 0.3
            if abs(speed) < min_speed:
                # The predicted landing is right on top of the boss (dx
                # near zero) -- still commit to *some* horizontal motion
                # toward the player's actual (not predicted) position,
                # rather than hopping straight up and accomplishing nothing.
                direction = 1.0 if player.center_x >= boss.center_x else -1.0
                speed = min_speed * direction
            boss.facing_right = speed > 0
            boss.x_vel = speed
            boss.y_vel = -hop_impulse
            boss.on_ground = False
            interval_min = SLIME_KING_HOP_INTERVAL_MIN_S / speed_mult
            interval_max = SLIME_KING_HOP_INTERVAL_MAX_S / speed_mult
            boss.hop_cooldown_remaining = random.uniform(interval_min, interval_max)
        else:
            boss.x_vel = 0.0

    if boss.x_vel != 0:
        # tile_collision.try_step_up is height- and width-aware (see its
        # docstring), so it correctly climbs a bump under the boss's tall
        # (1.8-tile), wide (2.4-tile) hop path instead of move_axis zeroing
        # x_vel dead on contact and stalling the boss (the "um bloco já
        # impede ele de me bater" / "preso em terreno desnivelado"
        # complaints). max_step_tiles=2: at this width, the boss's leading
        # edge can reach a column whose ground is a full 2 tiles higher
        # than the one under its own center, even on an otherwise smooth
        # 1-tile-per-column staircase -- see try_step_up's docstring.
        tile_collision.try_step_up(boss, world, 1 if boss.x_vel > 0 else -1, max_step_tiles=2)
    tile_collision.move_axis(boss, world, boss.x_vel, horizontal=True)
    landed = tile_collision.move_axis(boss, world, boss.y_vel, horizontal=False)
    if landed:
        boss.y_vel = 0.0
        boss.on_ground = True
    elif boss.y_vel < 0:
        boss.on_ground = False


def _fire_projectiles(boss: Boss, player) -> List[EnemyProjectile]:
    """One Slime Lob in phase 2; a SLIME_KING_SPREAD_COUNT-projectile fan
    once enraged (phase 3) -- the "crie projéteis" ask, plural, and a
    real step up in danger since dodging one lob is easy but dodging a
    spread means finding the gap between them."""
    dx = player.center_x - boss.center_x
    dy = (player.center_y - TILE_SIZE) - boss.center_y  # lead slightly above the player's center
    base_angle = math.atan2(dy, dx)

    if boss.phase_index < 2:
        angles = [base_angle]
    else:
        spread = math.radians(SLIME_KING_SPREAD_ANGLE_DEGREES)
        half = (SLIME_KING_SPREAD_COUNT - 1) / 2.0
        angles = [base_angle + (i - half) * spread for i in range(SLIME_KING_SPREAD_COUNT)]

    return [
        EnemyProjectile(
            boss.center_x, boss.center_y,
            SLIME_KING_LOB_SPEED * math.cos(angle), SLIME_KING_LOB_SPEED * math.sin(angle),
            SLIME_KING_LOB_DAMAGE,
        )
        for angle in angles
    ]
