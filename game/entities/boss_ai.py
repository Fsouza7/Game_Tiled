"""AI for the Slime King boss: three health-ratio phases, each adding a
distinct attack on top of the previous one's. Mirrors enemy_ai.py's shape
(a pure function over (boss, world, player, dt)), but Boss instances live
in GameApp's shared `enemies` list alongside regular enemies, and Boss
itself has no access to the projectile/enemies lists it needs to spawn
into -- so, like combat_system.try_attack returning a new Projectile
instead of appending to one, `update` returns what it spawned (an
optional EnemyProjectile, a list of minion Enemy instances) for GameApp
to actually add. See GameApp.step, which calls this in its own loop
(bosses are skipped by the regular enemy_ai.update loop).

Phase 1 (ratio > BOSS_PHASE_2_HEALTH_RATIO): hops toward the player,
contact damage only -- identical shape to the regular Slime's AI, just
bigger/harder.
Phase 2 (<= BOSS_PHASE_2_HEALTH_RATIO): also lobs a gravity-arced Slime
Lob projectile at the player on a cooldown.
Phase 3 (<= BOSS_PHASE_3_HEALTH_RATIO): enrages once (summons
SLIME_KING_MINION_COUNT regular Slimes), hops/lobs faster, and every
landing triggers a radius shockwave (stomp_pending -- see
combat_system.resolve_boss_stomp) that can hit the player without a
direct hitbox overlap.
"""
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
    SLIME_KING_PHASE_SPEED_MULT, SLIME_KING_LOB_DAMAGE, SLIME_KING_LOB_COOLDOWN_S,
    SLIME_KING_LOB_SPEED, SLIME_KING_MINION_COUNT,
)
from game.world.world import World

SLIME_MINION_ID = "slime"


def _phase_for_ratio(ratio: float) -> int:
    if ratio <= BOSS_PHASE_3_HEALTH_RATIO:
        return 2
    if ratio <= BOSS_PHASE_2_HEALTH_RATIO:
        return 1
    return 0


def update(boss: Boss, world: World, player, dt: float) -> Tuple[Optional[EnemyProjectile], List[Enemy]]:
    boss.invulnerability_remaining = max(0.0, boss.invulnerability_remaining - dt)
    boss.stomp_pending = False
    if not boss.alive:
        return None, []

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

    projectile = None
    if boss.phase_index >= 1:
        boss.ranged_cooldown_remaining -= dt
        if boss.ranged_cooldown_remaining <= 0.0:
            projectile = _fire_lob(boss, player)
            boss.ranged_cooldown_remaining = SLIME_KING_LOB_COOLDOWN_S / SLIME_KING_PHASE_SPEED_MULT[boss.phase_index]

    return projectile, minions


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
            direction = 1 if player.center_x > boss.center_x else -1
            boss.facing_right = direction > 0
            boss.x_vel = direction * boss.enemy_def.move_speed * speed_mult
            boss.y_vel = -SLIME_KING_HOP_IMPULSE * min(1.15, speed_mult)
            boss.on_ground = False
            interval_min = SLIME_KING_HOP_INTERVAL_MIN_S / speed_mult
            interval_max = SLIME_KING_HOP_INTERVAL_MAX_S / speed_mult
            boss.hop_cooldown_remaining = random.uniform(interval_min, interval_max)
        else:
            boss.x_vel = 0.0

    tile_collision.move_axis(boss, world, boss.x_vel, horizontal=True)
    landed = tile_collision.move_axis(boss, world, boss.y_vel, horizontal=False)
    if landed:
        boss.y_vel = 0.0
        boss.on_ground = True
    elif boss.y_vel < 0:
        boss.on_ground = False


def _fire_lob(boss: Boss, player) -> EnemyProjectile:
    dx = player.center_x - boss.center_x
    dy = (player.center_y - TILE_SIZE) - boss.center_y  # lead slightly above the player's center
    distance = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
    return EnemyProjectile(
        boss.center_x, boss.center_y,
        SLIME_KING_LOB_SPEED * dx / distance, SLIME_KING_LOB_SPEED * dy / distance,
        SLIME_KING_LOB_DAMAGE,
    )
