"""Combat rules: melee/ranged attacks, projectile updates, contact damage,
knockback. Kept separate from Player/Enemy so those stay physics/AI-only."""
import logging
import math
from typing import List, Optional, Tuple

from game.combat.projectile import Projectile
from game.entities.enemy import Enemy
from game.items import item_registry
from game.settings import (
    TILE_SIZE, MELEE_REACH_TILES, MELEE_ARC_DEGREES, MELEE_SWING_VISUAL_DURATION_S,
    MELEE_MIN_TARGET_SIZE_TILES, KNOCKBACK_SPEED, KNOCKBACK_UPWARD_SPEED,
    PROJECTILE_SPEED, PROJECTILE_GRAVITY_SCALE, GRAVITY, WORLD_WIDTH_TILES,
    WORLD_HEIGHT_TILES, PLAYER_HIT_INVULNERABILITY_S, MIN_DAMAGE_AFTER_DEFENSE,
)
from game.world.world import World
from game.world import tile_registry

logger = logging.getLogger(__name__)


def _knockback_enemy(enemy: Enemy, from_x: float) -> None:
    direction = 1.0 if enemy.center_x >= from_x else -1.0
    enemy.x_vel = direction * KNOCKBACK_SPEED
    enemy.y_vel = -KNOCKBACK_UPWARD_SPEED
    enemy.on_ground = False


def _knockback_player(player, from_x: float) -> None:
    direction = 1.0 if player.center_x >= from_x else -1.0
    player.x_vel = direction * KNOCKBACK_SPEED
    player.y_vel = -KNOCKBACK_UPWARD_SPEED
    player.on_ground = False


def _aim_direction(player, aim_world_pos) -> Tuple[float, float]:
    dx = aim_world_pos[0] - player.center_x
    dy = aim_world_pos[1] - player.center_y
    distance = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
    return dx / distance, dy / distance


def try_attack(player, world: World, enemies: List[Enemy], aim_world_pos) -> Optional[Projectile]:
    """Attempts an attack with the currently selected item, if it's a
    weapon and the cooldown/ammo allow it. Returns a new Projectile for a
    successful ranged shot, otherwise None (melee hits are applied directly
    to `enemies`)."""
    selected = player.inventory.get_selected_item()
    if selected is None or not player.can_attack():
        return None
    item_def = item_registry.get(selected.item_id)
    if not item_def.is_weapon:
        return None

    aim_dx, aim_dy = _aim_direction(player, aim_world_pos)
    player.facing_right = aim_dx >= 0

    if item_def.is_ranged:
        return _try_ranged_attack(player, item_def, aim_dx, aim_dy)
    _try_melee_attack(player, item_def, enemies, aim_dx, aim_dy)
    return None


def _try_melee_attack(player, item_def, enemies: List[Enemy], aim_dx: float, aim_dy: float) -> None:
    player.attack_cooldown_remaining = 1.0 / max(0.1, item_def.speed)
    player.melee_swing_timer = MELEE_SWING_VISUAL_DURATION_S
    player.melee_swing_aim = (aim_dx, aim_dy)

    reach_px = MELEE_REACH_TILES * TILE_SIZE + player.width / 2
    half_arc_cos = math.cos(math.radians(MELEE_ARC_DEGREES / 2))

    for enemy in enemies:
        if not enemy.alive:
            continue
        to_enemy_x = enemy.center_x - player.center_x
        to_enemy_y = enemy.center_y - player.center_y
        distance = (to_enemy_x ** 2 + to_enemy_y ** 2) ** 0.5
        target_size = max(enemy.width, enemy.height, MELEE_MIN_TARGET_SIZE_TILES * TILE_SIZE)
        max_distance = reach_px + target_size / 2
        if distance > max_distance:
            continue
        # Within a cone centered on the aim direction, not just left/right --
        # a real swing hits whatever the mouse is pointed at.
        facing_dot = 1.0 if distance < 1e-6 else (to_enemy_x * aim_dx + to_enemy_y * aim_dy) / distance
        if facing_dot < half_arc_cos:
            continue
        if enemy.take_damage(item_def.damage):
            _knockback_enemy(enemy, player.center_x)


def _try_ranged_attack(player, item_def, aim_dx: float, aim_dy: float) -> Optional[Projectile]:
    if item_def.ammo_item_id is None or player.inventory.count_item(item_def.ammo_item_id) <= 0:
        return None

    player.inventory.remove_item(item_def.ammo_item_id, 1)
    player.attack_cooldown_remaining = 1.0 / max(0.1, item_def.speed)

    return Projectile(
        player.center_x, player.center_y,
        PROJECTILE_SPEED * aim_dx, PROJECTILE_SPEED * aim_dy,
        item_def.damage,
    )


def update_projectiles(projectiles: List[Projectile], world: World, enemies: List[Enemy], dt: float) -> List[Projectile]:
    survivors = []
    for projectile in projectiles:
        projectile.time_remaining -= dt
        projectile.y_vel += GRAVITY * PROJECTILE_GRAVITY_SCALE
        projectile.x += projectile.x_vel
        projectile.y += projectile.y_vel

        if projectile.time_remaining <= 0:
            continue
        if not (0 <= projectile.x < WORLD_WIDTH_TILES * TILE_SIZE and 0 <= projectile.y < WORLD_HEIGHT_TILES * TILE_SIZE):
            continue

        tile_x, tile_y = int(projectile.center_x // TILE_SIZE), int(projectile.center_y // TILE_SIZE)
        if world.is_solid(tile_x, tile_y):
            continue

        hit_enemy = False
        for enemy in enemies:
            if enemy.alive and projectile.rect.colliderect(enemy.rect):
                if enemy.take_damage(projectile.damage):
                    _knockback_enemy(enemy, projectile.x)
                hit_enemy = True
                break
        if hit_enemy:
            continue

        survivors.append(projectile)
    return survivors


def resolve_contact_damage(player, enemies: List[Enemy]) -> None:
    if not player.alive or player.is_invulnerable():
        return
    for enemy in enemies:
        if enemy.alive and player.rect.colliderect(enemy.rect):
            raw_damage = enemy.enemy_def.contact_damage
            damage = max(MIN_DAMAGE_AFTER_DEFENSE, raw_damage - player.equipment.total_defense())
            player.take_damage(damage)
            player.invulnerability_remaining = PLAYER_HIT_INVULNERABILITY_S
            _knockback_player(player, enemy.center_x)
            return


def resolve_hazard_damage(player, world: World) -> None:
    """Damages the player for overlapping a hazard tile (e.g. placed
    Spikes -- see TileDef.contact_damage), the tile equivalent of
    resolve_contact_damage above."""
    if not player.alive or player.is_invulnerable():
        return
    rect = player.rect
    left_tile = rect.left // TILE_SIZE
    right_tile = (rect.right - 1) // TILE_SIZE
    top_tile = rect.top // TILE_SIZE
    bottom_tile = (rect.bottom - 1) // TILE_SIZE
    for tx in range(left_tile, right_tile + 1):
        for ty in range(top_tile, bottom_tile + 1):
            tile_def = tile_registry.get(world.get_tile(tx, ty))
            if tile_def.contact_damage > 0:
                damage = max(MIN_DAMAGE_AFTER_DEFENSE, tile_def.contact_damage - player.equipment.total_defense())
                player.take_damage(damage)
                player.invulnerability_remaining = PLAYER_HIT_INVULNERABILITY_S
                return


def resolve_hazard_feature_damage(player, world: World) -> None:
    """Damages the player for overlapping a moving hazard (Saw/Rock Head/
    Spike Head -- see game/world/hazard_feature.py), the entity equivalent
    of resolve_hazard_damage above, complete with knockback since these are
    meant to fling you clear of danger, not just sting."""
    if not player.alive or player.is_invulnerable():
        return
    player_rect = player.rect
    for anchor in world.iter_hazard_anchors():
        hazard_rect = anchor.current_rect(world.elapsed_s)
        if hazard_rect.colliderect(player_rect):
            damage = max(MIN_DAMAGE_AFTER_DEFENSE, anchor.contact_damage - player.equipment.total_defense())
            player.take_damage(damage)
            player.invulnerability_remaining = PLAYER_HIT_INVULNERABILITY_S
            _knockback_player(player, hazard_rect.centerx)
            return
