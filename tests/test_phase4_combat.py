"""Headless tests for Phase 4 combat: enemy registry, AI collision helpers,
melee/ranged attacks, projectiles, contact damage/knockback, and the enemy
spawner's population cap.
"""
import os
import random

import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, ENEMY_MAX_ALIVE_DAY,
    PLAYER_HIT_INVULNERABILITY_S, CHUNK_WIDTH,
)
from game.entities import tile_collision
from game.entities.enemy import Enemy
from game.entities.enemy_def import AIType
from game.entities import enemy_registry
from game.entities.enemy_spawner import EnemySpawner
from game.entities.player import Player
from game.combat import combat_system
from game.combat.projectile import Projectile
from game.crafting import recipe_registry
from game.items import item_registry
from game.world.world import World
from game.world.tile_registry import GRASS_ID, STONE_ID, AIR_ID


def _make_player_at(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    return Player(x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


def _flatten_ground(world, start_x, end_x, ground_row):
    """Forces a flat, deterministic run of solid ground (and clear air
    above it) across [start_x, end_x), bypassing world_generator's noise
    entirely -- so a test that carves a specific ledge/pit at a known row
    isn't at the mercy of this seed's natural terrain height varying
    between columns."""
    for col in range(start_x, end_x):
        chunk = world.get_or_create_chunk(world.chunk_index_for(col))
        local_x = col % CHUNK_WIDTH
        chunk.set_tile(local_x, ground_row, STONE_ID)
        chunk.set_tile(local_x, ground_row - 1, AIR_ID)
        chunk.set_tile(local_x, ground_row - 2, AIR_ID)


# --- registry sanity ---

def test_enemy_registry_has_the_expected_types():
    enemies = enemy_registry.all_enemies()
    assert {"slime", "crawler", "duskwing", "scorpion", "slime_king", "frost_hopper", "swamp_mosquito"} <= {e.id for e in enemies}


def test_enemy_drops_reference_real_items():
    for enemy_def in enemy_registry.all_enemies():
        if enemy_def.drop_item_id is not None:
            item_registry.get(enemy_def.drop_item_id)  # raises if missing
            assert 0.0 < enemy_def.drop_chance <= 1.0
            assert enemy_def.drop_min <= enemy_def.drop_max


def test_combat_recipes_are_registered():
    sword = recipe_registry.get("wood_sword")
    bow = recipe_registry.get("wood_bow")
    arrow = recipe_registry.get("arrow")
    assert sword.result_item_id == "wood_sword"
    assert bow.result_item_id == "wood_bow"
    assert arrow.result_quantity > 1  # crafting arrows should be efficient


def test_weapon_items_have_combat_fields():
    sword = item_registry.get("wood_sword")
    bow = item_registry.get("wood_bow")
    assert sword.is_weapon and not sword.is_ranged
    assert bow.is_weapon and bow.is_ranged
    assert bow.ammo_item_id == "arrow"


# --- shared tile-collision helpers (used by both Player and enemy AI) ---

def test_ground_and_wall_probes():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1

    enemy_def = enemy_registry.get("crawler")
    # Land exactly on the grass row's top (what gravity+collision would
    # produce), not the raw spawn position, which can leave the entity a
    # sub-pixel gap above the ground since its height isn't a whole tile.
    enemy = Enemy(enemy_def, x * TILE_SIZE, surface_y * TILE_SIZE - enemy_def.height_tiles * TILE_SIZE)

    assert tile_collision.has_ground_ahead(enemy, world, 1) is True
    assert tile_collision.is_solid_ahead(enemy, world, 1) is False

    # Break just the top tile ahead -- ground AI tolerates a 1-tile step
    # down (real ground still one row further down) the same way it
    # tolerates a 1-tile step up, so this alone should NOT read as a cliff.
    world.try_break_tile(x + 1, surface_y)
    assert tile_collision.has_ground_ahead(enemy, world, 1) is True

    # Break the tile below that too -- now it's a genuine 2+ tile drop.
    world.try_break_tile(x + 1, surface_y + 1)
    assert tile_collision.has_ground_ahead(enemy, world, 1) is False


# --- enemy AI ---

def test_slime_hops_and_lands():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    enemy = Enemy(enemy_registry.get("slime"), x * TILE_SIZE, (surface_y - 5) * TILE_SIZE)
    player = _make_player_at(world, x + 30)  # far away, out of chase range

    from game.entities import enemy_ai
    landed_at_least_once = False
    for _ in range(300):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
        if enemy.on_ground:
            landed_at_least_once = True
    assert landed_at_least_once


def test_crawler_does_not_walk_off_a_ledge():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    # A flat, deterministic approach (not this seed's natural terrain,
    # which can rise/fall between columns -- see test_crawler_climbs_a_
    # one_tile_ledge_instead_of_turning_around) so the only thing in the
    # crawler's path really is the pit this test digs.
    _flatten_ground(world, x, x + 5, surface_y)
    # Carve a genuinely uncrossable pit a couple tiles to the right.
    for dy in range(0, 6):
        world.try_break_tile(x + 2, surface_y + dy)

    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemy.facing_right = True  # force it to walk toward the pit deterministically
    player = _make_player_at(world, x - 30)  # far away, out of chase range

    from game.entities import enemy_ai
    for _ in range(600):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
        assert enemy.x < (x + 2) * TILE_SIZE + TILE_SIZE  # never crosses the pit


def test_crawler_climbs_a_one_tile_ledge_instead_of_turning_around():
    """Regression test: ground AI has no jump input (unlike the player),
    so before tile_collision.try_step_up existed, a WALK enemy turned
    around at *any* solid tile ahead -- including an ordinary 1-tile rise
    in the terrain, not just a real wall. Given how bumpy generated ground
    already is, that left ground enemies barely able to move at all."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    _flatten_ground(world, x, x + 3, surface_y)
    # A single-tile step up starting two columns ahead -- ground one tile
    # higher, with clear air above it to actually stand in.
    _flatten_ground(world, x + 2, x + 6, surface_y - 1)

    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemy.facing_right = True
    player = _make_player_at(world, x - 30)  # far away, out of chase range

    from game.entities import enemy_ai
    furthest_x = enemy.x
    for _ in range(300):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
        furthest_x = max(furthest_x, enemy.x)

    # No chase target pulling it onward, so with has_ground_ahead's
    # matching 1-tile step-down tolerance it's free to wander back down
    # again afterward (same as it would over any other ordinary bump) --
    # the thing this test actually cares about is that it *can* climb the
    # step at all, which "how far right did it ever get" proves without
    # being sensitive to exactly which side of the step it settles on by
    # the time the loop ends.
    assert furthest_x > (x + 3) * TILE_SIZE
    assert enemy.on_ground


def test_crawler_does_not_tunnel_through_a_low_cave_ceiling():
    """Regression test: try_step_up originally only checked headroom in
    the column ahead, not the entity's own current column. In a 1-tile-
    tall corridor (solid floor, solid ceiling directly overhead -- exactly
    what natural caves look like) with a climbable step ahead, that let
    the enemy snap up into its own ceiling tile every frame, tunneling
    straight up through solid rock instead of correctly refusing to climb
    for lack of headroom."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    ground_row = 60

    # A tight 1-tile corridor: floor at ground_row, one tile of walkable
    # air, solid ceiling directly above that.
    for col in range(x, x + 6):
        chunk = world.get_or_create_chunk(world.chunk_index_for(col))
        local_x = col % CHUNK_WIDTH
        chunk.set_tile(local_x, ground_row, STONE_ID)
        chunk.set_tile(local_x, ground_row - 1, AIR_ID)
        chunk.set_tile(local_x, ground_row - 2, STONE_ID)
    # A step up starting a couple columns ahead -- the floor rises into
    # what was walkable air, but the ceiling rises with it, so there's
    # still only 1 tile of clearance at the new height too.
    for col in range(x + 2, x + 6):
        chunk = world.get_or_create_chunk(world.chunk_index_for(col))
        local_x = col % CHUNK_WIDTH
        chunk.set_tile(local_x, ground_row - 1, STONE_ID)
        chunk.set_tile(local_x, ground_row - 2, AIR_ID)
        chunk.set_tile(local_x, ground_row - 3, STONE_ID)

    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (ground_row - 1) * TILE_SIZE)  # the corridor's walkable row
    enemy.facing_right = True
    player = _make_player_at(world, x - 30)  # far away, out of chase range

    from game.entities import enemy_ai
    for _ in range(120):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
        tile_x, tile_y = int(enemy.x // TILE_SIZE), int(enemy.y // TILE_SIZE)
        assert not world.is_solid(tile_x, tile_y), "enemy tunneled into solid rock"


def test_crawler_does_not_freeze_on_a_narrow_perch_with_a_safe_step_down():
    """Regression test (found by playtesting this session's climb fix): a
    1-tile-wide perch with an unclimbable wall on one side and an ordinary
    1-tile step down on the other used to trap a chasing crawler in a
    zero-net-progress oscillation. Direction is recomputed fresh from the
    player's position every frame; the moment it edges toward the safe
    side, the small y offset from falling/settling nudges it just outside
    ENEMY_CHASE_RADIUS_TILES, so that frame falls back to stale
    `facing_right` instead -- and before has_ground_ahead tolerated a
    1-tile descent, that direction read as a cliff too, flipping it right
    back toward the wall. Net effect: x_vel alternates +/-speed every
    other frame (never literally 0, which is why a naive "x_vel == 0"
    check wouldn't have caught this), and the enemy never actually goes
    anywhere -- visibly frozen just out of melee reach."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    row = 50

    def _set_column(col, floor_row, wall_from=None, wall_to=None):
        chunk = world.get_or_create_chunk(world.chunk_index_for(col))
        local_x = col % CHUNK_WIDTH
        for y in range(row - 10, row + 3):
            chunk.set_tile(local_x, y, AIR_ID)
        chunk.set_tile(local_x, floor_row, STONE_ID)
        if wall_from is not None:
            for y in range(wall_from, wall_to):
                chunk.set_tile(local_x, y, STONE_ID)

    _set_column(x, row)  # the perch itself
    for wall_col in (x + 1, x + 2):  # a tall, genuinely unclimbable wall
        _set_column(wall_col, row, wall_from=row - 6, wall_to=row + 1)
    for safe_col in (x - 1, x - 2, x - 3):  # an ordinary 1-tile step down
        _set_column(safe_col, row + 1)

    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (row - 1) * TILE_SIZE)
    enemy.facing_right = True  # Enemy.__init__ otherwise randomizes this (random.choice) -- pin it for a deterministic run
    start_x = enemy.x
    player = _make_player_at(world, x + 10)  # across the wall -- pulls chase direction into it every frame

    from game.entities import enemy_ai
    for _ in range(180):
        enemy_ai.update(enemy, world, player, dt=1 / 60)

    # The only direction that isn't a real wall is the safe step down, so
    # real progress means having gone meaningfully further that way --
    # not just still jittering within ~1 tile of where it started.
    assert start_x - enemy.x > TILE_SIZE, "enemy is stuck oscillating on the perch instead of taking the safe step down"


def test_duskwing_ignores_gravity_when_not_stunned():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    start_y = (surface_y - 20) * TILE_SIZE
    enemy = Enemy(enemy_registry.get("duskwing"), x * TILE_SIZE, start_y)
    player = _make_player_at(world, x + 30)

    from game.entities import enemy_ai
    for _ in range(120):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
    # A ground-bound enemy would have fallen dozens of tiles by now; a flyer
    # should stay roughly at its spawn altitude (small bob notwithstanding).
    assert abs(enemy.y - start_y) < TILE_SIZE * 3


def test_duskwing_climbs_over_a_wall_instead_of_getting_stuck_against_it():
    """Regression test: chasing straight at the player with no wall-
    routing logic used to mean a flyer just pressed into any wall/ledge
    directly between it and its target, forever, instead of rising up and
    over it like it would any other obstacle."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    flight_row = surface_y - 20

    wall_x = x + 4
    chunk = world.get_or_create_chunk(world.chunk_index_for(wall_x))
    for dy in range(-5, 6):
        chunk.set_tile(wall_x % CHUNK_WIDTH, flight_row + dy, STONE_ID)

    enemy = Enemy(enemy_registry.get("duskwing"), x * TILE_SIZE, flight_row * TILE_SIZE)
    player = _make_player_at(world, x + 8)
    player.y = flight_row * TILE_SIZE

    from game.entities import enemy_ai
    start_x = enemy.x
    for _ in range(240):
        enemy_ai.update(enemy, world, player, dt=1 / 60)

    assert enemy.x > start_x + TILE_SIZE * 2  # made real progress, not stuck at the wall
    assert enemy.y < flight_row * TILE_SIZE  # climbed above its start altitude to get over it


# --- melee combat ---

def test_melee_attack_damages_and_can_kill_with_drop():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)  # slot 0 is the starter pickaxe

    enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemies = [enemy]

    hits = 0
    while enemy.alive and hits < 20:
        # Simulate enough real time passing between swings for both the
        # player's attack cooldown and the enemy's hit-invulnerability
        # (normally decremented by enemy_ai.update, not called here) to
        # clear -- matches how these interact during real gameplay.
        player.attack_cooldown_remaining = 0.0
        enemy.invulnerability_remaining = 0.0
        combat_system.try_attack(player, world, enemies, (enemy.center_x, enemy.center_y))
        hits += 1

    assert enemy.defeated is True
    assert hits > 1  # one hit shouldn't one-shot a 20 hp slime with an 8 dmg sword


def test_melee_attack_hits_toward_aim_even_with_stale_facing():
    # Regression test: melee used to only ever hit in player.facing_right's
    # direction (left/right based on the last movement key), so an enemy
    # approaching from the side you're not currently facing was unhittable
    # even at point-blank range. It should now hit wherever the mouse aims.
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    player.facing_right = True  # stale: still "facing" right
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    enemy = Enemy(enemy_registry.get("slime"), (x - 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    combat_system.try_attack(player, world, [enemy], (enemy.center_x, enemy.center_y))
    assert enemy.health < enemy.enemy_def.max_health
    assert player.facing_right is False  # aiming left updated the facing too


def test_melee_attack_misses_outside_the_aim_cone():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    # Aim straight left while the enemy sits to the right -- outside the cone.
    combat_system.try_attack(player, world, [enemy], (player.center_x - 500, player.center_y))
    assert enemy.health == enemy.enemy_def.max_health


def test_melee_hit_detection_is_forgiving_for_small_enemies():
    # Regression test for the "small enemies are hard to hit" complaint:
    # place a slime (0.8x0.6 tiles -- smaller than MELEE_MIN_TARGET_SIZE_TILES)
    # right at the edge of what its *raw* size would allow, and confirm the
    # forgiving minimum target size still lets the swing connect.
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    from game.settings import MELEE_REACH_TILES, MELEE_MIN_TARGET_SIZE_TILES
    raw_size_px = 0.8 * TILE_SIZE  # slime's actual width/height in pixels
    min_size_px = MELEE_MIN_TARGET_SIZE_TILES * TILE_SIZE
    assert min_size_px > raw_size_px  # sanity: the floor actually matters here

    reach_px = MELEE_REACH_TILES * TILE_SIZE + player.width / 2
    # Distance that's beyond raw-size reach but within min-size-floor reach.
    distance = reach_px + raw_size_px / 2 + 2
    assert distance <= reach_px + min_size_px / 2

    enemy_def = enemy_registry.get("slime")
    enemy_x = player.center_x + distance - enemy_def.width_tiles * TILE_SIZE / 2
    enemy_y = player.center_y - enemy_def.height_tiles * TILE_SIZE / 2  # same center_y as the player
    enemy = Enemy(enemy_def, enemy_x, enemy_y)
    combat_system.try_attack(player, world, [enemy], (enemy.center_x, enemy.center_y))
    assert enemy.health < enemy.enemy_def.max_health


def test_melee_attack_starts_swing_visual():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    assert player.melee_swing_timer == 0.0
    combat_system.try_attack(player, world, [], (player.center_x + 100, player.center_y))
    assert player.melee_swing_timer > 0.0
    assert player.melee_swing_aim[0] > 0  # aimed to the right


def test_ranged_attack_updates_facing_toward_aim():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    player.facing_right = True
    player.inventory.add_item("wood_bow", 1)
    player.inventory.add_item("arrow", 5)
    player.inventory.select_hotbar(1)

    projectile = combat_system.try_attack(player, world, [], (player.center_x - 200, player.center_y))
    assert projectile is not None
    assert projectile.x_vel < 0
    assert player.facing_right is False


def test_melee_attack_out_of_range_does_nothing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    far_enemy = Enemy(enemy_registry.get("slime"), (x + 20) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    combat_system.try_attack(player, world, [far_enemy], (far_enemy.center_x, far_enemy.center_y))
    assert far_enemy.health == far_enemy.enemy_def.max_health


def test_melee_without_weapon_selected_does_nothing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)  # only has the starter pickaxe selected
    enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    combat_system.try_attack(player, world, [enemy], (enemy.center_x, enemy.center_y))
    assert enemy.health == enemy.enemy_def.max_health


# --- ranged combat ---

def test_ranged_attack_requires_and_consumes_ammo():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_bow", 1)
    player.inventory.select_hotbar(1)

    # No arrows yet -- should fail.
    result = combat_system.try_attack(player, world, [], (player.center_x + 100, player.center_y))
    assert result is None

    player.inventory.add_item("arrow", 5)
    projectile = combat_system.try_attack(player, world, [], (player.center_x + 100, player.center_y))
    assert isinstance(projectile, Projectile)
    assert player.inventory.count_item("arrow") == 4
    assert projectile.x_vel > 0  # aimed to the right


def test_projectile_hits_enemy_and_is_removed():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    surface_y = world.surface_spawn_y(x) + 1
    enemy = Enemy(enemy_registry.get("slime"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    projectile = Projectile(enemy.center_x, enemy.center_y, 0.0, 0.0, damage=999.0)

    survivors = combat_system.update_projectiles(player, [projectile], world, [enemy], dt=1 / 60)
    assert survivors == []
    assert enemy.defeated is True


def test_projectile_expires_after_lifetime():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    projectile = Projectile(TILE_SIZE * 10, TILE_SIZE * 10, 0.0, 0.0, damage=1.0)
    projectile.time_remaining = 0.001
    survivors = combat_system.update_projectiles(player, [projectile], world, [], dt=1 / 60)
    assert survivors == []


def test_projectile_destroyed_by_solid_tile():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    surface_y = world.surface_spawn_y(x) + 1
    assert world.get_tile(x, surface_y) == GRASS_ID
    projectile = Projectile(x * TILE_SIZE, surface_y * TILE_SIZE, 0.0, 0.0, damage=1.0)
    survivors = combat_system.update_projectiles(player, [projectile], world, [], dt=1 / 60)
    assert survivors == []


# --- contact damage / invulnerability ---

def test_contact_damage_applies_once_then_respects_invulnerability():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)

    starting_hp = player.health
    expected_damage = enemy.enemy_def.contact_damage - combat_system.player_total_defense(player)
    combat_system.resolve_contact_damage(player, [enemy])
    assert player.health == starting_hp - expected_damage
    assert player.is_invulnerable() is True

    combat_system.resolve_contact_damage(player, [enemy])  # still overlapping
    assert player.health == starting_hp - expected_damage  # unchanged


def test_enemy_invulnerability_blocks_repeat_damage():
    enemy = Enemy(enemy_registry.get("slime"), 0, 0)
    assert enemy.take_damage(5.0) is True
    assert enemy.take_damage(5.0) is False  # still in i-frames
    assert enemy.health == enemy.enemy_def.max_health - 5.0


def test_player_take_damage_queues_a_popup_at_the_hit_not_after_respawn():
    from game.rendering.damage_numbers import drain_popups

    player = Player(120.0, 80.0)
    hit_x, hit_y = player.center_x, player.y
    player.take_damage(player.max_health + 25)  # lethal -- respawns at spawn
    pops = drain_popups(player)
    assert len(pops) == 1
    x, y, amount = pops[0]
    assert (x, y) == (hit_x, hit_y)
    assert amount == player.max_health + 25
    assert player.pending_damage_popups == []


def test_enemy_i_frames_do_not_queue_a_second_popup():
    from game.rendering.damage_numbers import drain_popups

    enemy = Enemy(enemy_registry.get("slime"), 0, 0)
    assert enemy.take_damage(5.0) is True
    assert enemy.take_damage(5.0) is False
    pops = drain_popups(enemy)
    assert len(pops) == 1
    assert pops[0][2] == 5.0


def test_damage_numbers_rise_and_expire():
    from game.rendering.damage_numbers import DamageNumbers
    from game.settings import DAMAGE_POPUP_LIFETIME_S, DAMAGE_POPUP_RISE_PX_PER_S

    numbers = DamageNumbers()
    numbers.spawn(10.0, 50.0, 8.0, on_player=True)
    assert len(numbers.popups) == 1
    start_y = numbers.popups[0].y
    numbers.update(0.2)
    assert numbers.popups[0].y < start_y
    assert abs((start_y - numbers.popups[0].y) - DAMAGE_POPUP_RISE_PX_PER_S * 0.2) < 0.01
    numbers.update(DAMAGE_POPUP_LIFETIME_S)
    assert numbers.popups == []


def test_game_app_draws_player_and_enemy_hits():
    from game.core.game_app import GameApp
    from game.rendering.damage_numbers import drain_popups

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.player.take_damage(4.0)
        enemy = Enemy(enemy_registry.get("slime"), app.player.x + 40, app.player.y)
        enemy.take_damage(9.0)
        app.enemies.append(enemy)
        app._harvest_damage_popups()
        assert drain_popups(app.player) == []
        assert {p.amount for p in app.damage_numbers.popups} == {4.0, 9.0}
        assert {p.on_player for p in app.damage_numbers.popups} == {True, False}
        app.step(dt=1 / 60)  # real draw path, including _draw_damage_numbers
    finally:
        pygame.quit()


def test_roll_drop_matches_def_bounds():
    random.seed(42)
    enemy = Enemy(enemy_registry.get("slime"), 0, 0)
    got_a_drop = False
    for _ in range(50):
        drop = enemy.roll_drop()
        if drop is not None:
            got_a_drop = True
            item_id, qty = drop
            item_registry.get(item_id)
            assert enemy.enemy_def.drop_min <= qty <= enemy.enemy_def.drop_max
    assert got_a_drop  # 80% chance per roll, 50 rolls -- practically certain


# --- spawner ---

def test_spawner_respects_max_alive_cap():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    spawner = EnemySpawner()
    enemies = []

    for _ in range(2000):
        spawner.time_until_next_spawn = 0.0  # force an attempt every tick
        spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
        enemies = [e for e in enemies if e.alive]
        assert len(enemies) <= ENEMY_MAX_ALIVE_DAY


def test_flying_enemies_spawn_above_the_ground():
    from game.entities.enemy_spawner import _spawn_y_tiles

    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    ground_air = surface_y - 1
    slime_y = _spawn_y_tiles(world, x, enemy_registry.get("slime"))
    bat_y = _spawn_y_tiles(world, x, enemy_registry.get("duskwing"))
    assert slime_y == ground_air
    assert bat_y < slime_y
    assert not world.is_solid(x, bat_y)


def test_spawner_despawns_far_enemies():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    far_enemy = Enemy(enemy_registry.get("slime"), 0, 0)  # very far from x
    spawner = EnemySpawner()
    spawner.time_until_next_spawn = 999.0  # don't also try to spawn this tick
    enemies = [far_enemy]
    spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
    assert far_enemy.alive is False


def test_enemy_sprites_from_enemies_folder():
    from game.rendering import assets
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT
    from game.rendering.renderer import Renderer

    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    assert os.path.isfile(assets.MINI_BAT_PATH)
    assert os.path.isfile(assets.SLIME_IDLE_PATH)
    assert os.path.isfile(assets.SCORPION_IDLE_PATH)

    bat = assets.load_duskwing_animations(assets.DUSKWING_SPRITE_SIZE)
    assert len(bat[("idle", "right")]) == 3
    assert len(bat[("chase", "right")]) == 4
    assert len(bat[("hit", "right")]) == 1

    slime = assets.load_slime_animations(assets.SLIME_SPRITE_SIZE)
    assert len(slime[("idle", "right")]) == 9
    assert len(slime[("chase", "right")]) == 8
    assert len(slime[("hit", "right")]) == 1

    scorpion = assets.load_scorpion_animations(assets.SCORPION_SPRITE_SIZE)
    assert len(scorpion[("idle", "right")]) == 3
    assert len(scorpion[("chase", "right")]) == 3
    assert len(scorpion[("hit", "right")]) == 3

    assert os.path.isfile(assets.EYEBALL_PATH)
    crawler = assets.load_crawler_animations(assets.CRAWLER_SPRITE_SIZE)
    assert len(crawler[("idle", "right")]) == 6
    assert len(crawler[("chase", "right")]) == 4
    assert len(crawler[("hit", "right")]) == 1

    idle = bat[("idle", "right")][0]
    opaque = sum(
        1
        for y in range(0, idle.get_height(), 4)
        for x in range(0, idle.get_width(), 4)
        if idle.get_at((x, y))[3] > 0
    )
    assert opaque > 5

    renderer = Renderer()
    assert set(renderer.enemy_animations) >= {"duskwing", "slime", "slime_king", "scorpion", "frost_hopper", "swamp_mosquito", "crawler"}
    bat_enemy = Enemy(enemy_registry.get("duskwing"), 0, 0)
    assert renderer._enemy_animation_state(bat_enemy) == "idle"
    bat_enemy.x_vel = bat_enemy.enemy_def.move_speed
    assert renderer._enemy_animation_state(bat_enemy) == "chase"
    bat_enemy.invulnerability_remaining = 0.1
    assert renderer._enemy_animation_state(bat_enemy) == "hit"

    slime = Enemy(enemy_registry.get("slime"), 0, 0)
    assert renderer._enemy_animation_state(slime) == "idle"
    slime.x_vel = slime.enemy_def.move_speed
    assert renderer._enemy_animation_state(slime) == "chase"


# --- hit feedback: hit-spark particles + camera shake ---

def test_game_app_spawns_hit_sparks_and_shakes_camera_on_a_real_hit():
    """End-to-end through the real GameApp.step loop (_harvest_damage_
    popups), not just the underlying ParticleSystem/Camera methods --
    catches wiring mistakes (wrong color, forgetting to trigger the
    shake) the unit tests for those two systems wouldn't."""
    from game.core.game_app import GameApp
    from game.rendering.particles import HIT_SPARK

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        x = WORLD_WIDTH_TILES // 2
        surface_y = app.world.surface_spawn_y(x) + 1
        app.player.x, app.player.y = x * TILE_SIZE, (surface_y - 1) * TILE_SIZE
        app.player.inventory.add_item("wood_sword", 1)
        app.player.inventory.select_hotbar(1)

        enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
        app.enemies = [enemy]

        assert app.camera._shake_remaining_s == 0.0
        combat_system.try_attack(app.player, app.world, app.enemies, (enemy.center_x, enemy.center_y))
        app.player.take_damage(10.0)  # simulate the player also getting hit this frame

        app.step(dt=1 / 60)

        sparks = [p for p in app.particles.particles if p.kind == HIT_SPARK]
        assert len(sparks) > 0
        assert app.camera._shake_remaining_s > 0.0  # the player-taken hit triggered a shake
    finally:
        pygame.quit()


def test_dealing_damage_to_an_enemy_alone_does_not_shake_the_camera():
    """Only the player *taking* a hit shakes the camera -- dealing one to
    an enemy shouldn't, or a flurry of quick melee hits against weak
    enemies would turn into a nonstop screen wobble."""
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        x = WORLD_WIDTH_TILES // 2
        surface_y = app.world.surface_spawn_y(x) + 1
        app.player.x, app.player.y = x * TILE_SIZE, (surface_y - 1) * TILE_SIZE
        app.player.inventory.add_item("wood_sword", 1)
        app.player.inventory.select_hotbar(1)

        enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
        app.enemies = [enemy]

        combat_system.try_attack(app.player, app.world, app.enemies, (enemy.center_x, enemy.center_y))
        app.step(dt=1 / 60)

        assert app.camera._shake_remaining_s == 0.0
    finally:
        pygame.quit()


def test_draw_hit_spark_does_not_crash():
    import pygame as pg
    from game.rendering.renderer import Renderer
    from game.rendering.particles import ParticleSystem
    from game.rendering.damage_numbers import ENEMY_HIT_COLOR
    from game.core.camera import Camera
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    pg.init()
    pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pg.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    particles = ParticleSystem()
    particles.spawn_hit_spark(100.0, 100.0, color=ENEMY_HIT_COLOR)
    camera = Camera()

    renderer._draw_particles(window, particles, camera)
    particles.update(dt=0.3)  # past its lifetime
    renderer._draw_particles(window, particles, camera)  # empty list -- still shouldn't crash
