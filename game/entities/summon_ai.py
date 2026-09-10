"""AI for the player's active summon: chase and engage the nearest enemy
within range, otherwise hover near the player. Pure functions over
(summon, world, player, enemies, dt), mirroring enemy_ai.py's shape --
Summon itself stays a plain data holder (see summon.py).

Movement is flying-style (gravity ignored, no wall/ledge avoidance via
tile_collision.is_solid_ahead/has_ground_ahead) -- the same deliberate
simplification enemy_ai._update_fly already uses for Duskwing, which
sidesteps needing ground-pathing AI for a minion that must otherwise
follow the player anywhere (caves, over gaps, mid-air).
"""
import math

from game.entities import tile_collision
from game.entities.summon import Summon
from game.settings import TILE_SIZE, SUMMON_BOB_AMPLITUDE_TILES, SUMMON_BOB_FREQUENCY, SUMMON_HOVER_HEIGHT_TILES


def _distance_tiles(a_x, a_y, b_x, b_y) -> float:
    return ((a_x - b_x) ** 2 + (a_y - b_y) ** 2) ** 0.5 / TILE_SIZE


def nearest_enemy_in_range(center_x: float, center_y: float, enemies, radius_tiles: float):
    """The closest alive enemy within radius_tiles of (center_x, center_y),
    or None. Shared by summon_ai's targeting and combat_system's attack
    resolution so both agree on "who is this summon fighting"."""
    nearest = None
    nearest_distance = radius_tiles
    for enemy in enemies:
        if not enemy.alive:
            continue
        distance = _distance_tiles(center_x, center_y, enemy.center_x, enemy.center_y)
        if distance <= nearest_distance:
            nearest = enemy
            nearest_distance = distance
    return nearest


def update(summon: Summon, world, player, enemies, dt: float) -> None:
    summon.attack_cooldown_remaining = max(0.0, summon.attack_cooldown_remaining - dt)
    if not summon.alive:
        return

    summon_def = summon.summon_def
    target = nearest_enemy_in_range(summon.center_x, summon.center_y, enemies, summon_def.seek_radius_tiles)

    if target is not None:
        dx = target.center_x - summon.center_x
        dy = target.center_y - summon.center_y
        distance = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
        summon.x_vel = summon.move_speed * dx / distance
        summon.y_vel = summon.move_speed * dy / distance
        summon.facing_right = dx >= 0
    else:
        summon.bob_phase += dt * SUMMON_BOB_FREQUENCY
        home_x = player.center_x
        home_y = (
            player.center_y - SUMMON_HOVER_HEIGHT_TILES * TILE_SIZE
            + math.sin(summon.bob_phase) * SUMMON_BOB_AMPLITUDE_TILES * TILE_SIZE
        )
        if _distance_tiles(summon.center_x, summon.center_y, player.center_x, player.center_y) > summon_def.follow_distance_tiles:
            # Strayed too far (e.g. the player just teleported/respawned) --
            # snap back instead of a slow catch-up chase across the map.
            summon.x = home_x - summon.width / 2
            summon.y = home_y
            summon.x_vel = 0.0
            summon.y_vel = 0.0
        else:
            dx = home_x - summon.center_x
            dy = home_y - summon.center_y
            summon.x_vel = dx * 0.1
            summon.y_vel = dy * 0.1
            summon.facing_right = dx >= 0

    if summon.x_vel != 0 and tile_collision.is_solid_ahead(summon, world, 1 if summon.x_vel > 0 else -1):
        # No wall-routing logic (see module docstring) -- rather than
        # pressing straight into a ledge/wall it can't get around (this is
        # what made the summon look "stuck" on uneven terrain), rise up
        # and over it like it would any other obstacle.
        summon.y_vel = -abs(summon.move_speed)

    tile_collision.move_axis(summon, world, summon.x_vel, horizontal=True)
    tile_collision.move_axis(summon, world, summon.y_vel, horizontal=False)
