"""Basic AI for each enemy archetype. Pure functions over (enemy, world,
player, dt) so Enemy itself stays a plain data holder (see enemy.py).
"""
import math

from game.entities import tile_collision
from game.entities.enemy import Enemy
from game.entities.enemy_def import AIType
from game.settings import (
    GRAVITY, MAX_FALL_SPEED, TILE_SIZE, ENEMY_CHASE_RADIUS_TILES,
    SLIME_HOP_IMPULSE, SLIME_HOP_INTERVAL_MIN_S, SLIME_HOP_INTERVAL_MAX_S,
    FLYING_BOB_AMPLITUDE_TILES, FLYING_BOB_FREQUENCY, FLYING_STANDOFF_TILES,
)
from game.world.world import World
import random


def _distance_tiles(a_x, a_y, b_x, b_y) -> float:
    return ((a_x - b_x) ** 2 + (a_y - b_y) ** 2) ** 0.5 / TILE_SIZE


def _player_in_chase_range(enemy: Enemy, player) -> bool:
    return _distance_tiles(enemy.center_x, enemy.center_y, player.center_x, player.center_y) <= ENEMY_CHASE_RADIUS_TILES


def update(enemy: Enemy, world: World, player, dt: float) -> None:
    enemy.invulnerability_remaining = max(0.0, enemy.invulnerability_remaining - dt)
    if not enemy.alive:
        return

    ai_type = enemy.enemy_def.ai_type
    if ai_type == AIType.WALK:
        _update_walk(enemy, world, player, dt)
    elif ai_type == AIType.HOP:
        _update_hop(enemy, world, player, dt)
    elif ai_type == AIType.FLY:
        _update_fly(enemy, world, player, dt)


def _update_walk(enemy: Enemy, world: World, player, dt: float) -> None:
    # While stunned (just hit -- see ENEMY_HIT_INVULNERABILITY_S), let the
    # knockback velocity play out instead of the AI immediately overwriting it.
    if enemy.invulnerability_remaining <= 0.0:
        speed = enemy.enemy_def.move_speed
        direction = 1 if enemy.facing_right else -1

        if _player_in_chase_range(enemy, player):
            direction = 1 if player.center_x > enemy.center_x else -1

        if tile_collision.is_solid_ahead(enemy, world, direction):
            # A wall -- unless it's just a 1-tile ledge, which ground AI
            # (no jump input, unlike the player) climbs straight onto
            # instead of turning around at every bump in the terrain.
            if not (enemy.on_ground and tile_collision.try_step_up(enemy, world, direction)):
                direction *= -1
        elif not tile_collision.has_ground_ahead(enemy, world, direction):
            direction *= -1

        enemy.facing_right = direction > 0
        enemy.x_vel = direction * speed

    enemy.y_vel = min(enemy.y_vel + GRAVITY, MAX_FALL_SPEED)
    tile_collision.move_axis(enemy, world, enemy.x_vel, horizontal=True)
    landed = tile_collision.move_axis(enemy, world, enemy.y_vel, horizontal=False)
    if landed:
        enemy.y_vel = 0.0
        enemy.on_ground = True
    elif enemy.y_vel < 0:
        enemy.on_ground = False


def _update_hop(enemy: Enemy, world: World, player, dt: float) -> None:
    enemy.y_vel = min(enemy.y_vel + GRAVITY, MAX_FALL_SPEED)

    if enemy.on_ground and enemy.invulnerability_remaining <= 0.0:
        enemy.hop_cooldown_remaining -= dt
        if enemy.hop_cooldown_remaining <= 0.0:
            direction = 1 if player.center_x > enemy.center_x else -1
            if not _player_in_chase_range(enemy, player):
                direction = 1 if enemy.facing_right else -1
                if random.random() < 0.3:
                    direction *= -1
            enemy.facing_right = direction > 0
            enemy.x_vel = direction * enemy.enemy_def.move_speed
            enemy.y_vel = -SLIME_HOP_IMPULSE
            enemy.on_ground = False
            enemy.hop_cooldown_remaining = random.uniform(SLIME_HOP_INTERVAL_MIN_S, SLIME_HOP_INTERVAL_MAX_S)
        else:
            enemy.x_vel = 0.0

    if enemy.x_vel != 0:
        # HOP AI only sets x_vel once, at launch, and never revisits it
        # mid-air -- a 1-tile bump anywhere under the arc used to zero it
        # outright (move_axis on contact) and strand the enemy right
        # there, re-aiming at the same spot every following hop and
        # looking like it was bouncing in place against an invisible
        # wall. try_step_up climbs a genuine 1-tile ledge; a real wall is
        # still left alone.
        tile_collision.try_step_up(enemy, world, 1 if enemy.x_vel > 0 else -1)
    tile_collision.move_axis(enemy, world, enemy.x_vel, horizontal=True)
    landed = tile_collision.move_axis(enemy, world, enemy.y_vel, horizontal=False)
    if landed:
        enemy.y_vel = 0.0
        enemy.on_ground = True
    elif enemy.y_vel < 0:
        enemy.on_ground = False


def _update_fly(enemy: Enemy, world: World, player, dt: float) -> None:
    if enemy.invulnerability_remaining > 0.0:
        # Stunned: let the knockback arc play out under normal gravity
        # instead of the hover AI immediately overriding it.
        enemy.y_vel = min(enemy.y_vel + GRAVITY, MAX_FALL_SPEED)
    else:
        speed = enemy.enemy_def.move_speed
        enemy.bob_phase += dt * FLYING_BOB_FREQUENCY

        if _player_in_chase_range(enemy, player):
            dx = player.center_x - enemy.center_x
            dy = player.center_y - enemy.center_y
            distance = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
            if distance < FLYING_STANDOFF_TILES * TILE_SIZE:
                # Close enough to fight -- back off instead of camping
                # inside the player's hitbox and racking up free contact
                # damage every frame it's stuck there.
                enemy.x_vel = -speed * 0.5 * dx / distance
                enemy.y_vel = -speed * 0.5 * dy / distance
            else:
                enemy.x_vel = speed * dx / distance
                enemy.y_vel = speed * dy / distance
            enemy.facing_right = dx >= 0
        else:
            drift = 1 if enemy.facing_right else -1
            enemy.x_vel = drift * speed * 0.3
            # Steer toward a point on a sine wave (a bounded position),
            # rather than assigning a raw oscillating velocity -- the
            # latter integrates into unbounded drift since position here
            # is advanced by velocity directly (frame-based, no dt scale).
            target_y = enemy.bob_center_y + math.sin(enemy.bob_phase) * FLYING_BOB_AMPLITUDE_TILES * TILE_SIZE
            enemy.y_vel = (target_y - enemy.y) * 0.1

        if enemy.x_vel != 0 and tile_collision.is_solid_ahead(enemy, world, 1 if enemy.x_vel > 0 else -1):
            # Flying AI has no wall-routing logic (see module docstring) --
            # rather than pressing straight into a ledge/wall it can't get
            # around, rise up and over it like it would any other obstacle.
            enemy.y_vel = -abs(speed)

    attempted_x_vel = enemy.x_vel
    tile_collision.move_axis(enemy, world, enemy.x_vel, horizontal=True)
    tile_collision.move_axis(enemy, world, enemy.y_vel, horizontal=False)
    if attempted_x_vel != 0 and enemy.x_vel == 0:
        enemy.facing_right = not enemy.facing_right
