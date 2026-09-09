"""Headless tests for Phase 4 combat: enemy registry, AI collision helpers,
melee/ranged attacks, projectiles, contact damage/knockback, and the enemy
spawner's population cap.
"""
import random

import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, ENEMY_MAX_ALIVE,
    PLAYER_HIT_INVULNERABILITY_S,
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
from game.world.tile_registry import GRASS_ID


def _make_player_at(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    return Player(x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


# --- registry sanity ---

def test_enemy_registry_has_the_expected_types():
    enemies = enemy_registry.all_enemies()
    assert {e.id for e in enemies} == {"slime", "crawler", "duskwing", "scorpion"}


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

    # Carve a pit directly ahead -- now there should be no ground there.
    world.try_break_tile(x + 1, surface_y)
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
    # Carve a pit a few tiles to the right so the crawler must turn around.
    for dy in range(0, 5):
        world.try_break_tile(x + 3, surface_y + dy)

    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemy.facing_right = True  # force it to walk toward the pit deterministically
    player = _make_player_at(world, x - 30)  # far away, out of chase range

    from game.entities import enemy_ai
    for _ in range(600):
        enemy_ai.update(enemy, world, player, dt=1 / 60)
        assert enemy.x < (x + 3) * TILE_SIZE + TILE_SIZE  # never crosses the pit


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
    surface_y = world.surface_spawn_y(x) + 1
    enemy = Enemy(enemy_registry.get("slime"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    projectile = Projectile(enemy.center_x, enemy.center_y, 0.0, 0.0, damage=999.0)

    survivors = combat_system.update_projectiles([projectile], world, [enemy], dt=1 / 60)
    assert survivors == []
    assert enemy.defeated is True


def test_projectile_expires_after_lifetime():
    world = World(DEFAULT_SEED)
    projectile = Projectile(TILE_SIZE * 10, TILE_SIZE * 10, 0.0, 0.0, damage=1.0)
    projectile.time_remaining = 0.001
    survivors = combat_system.update_projectiles([projectile], world, [], dt=1 / 60)
    assert survivors == []


def test_projectile_destroyed_by_solid_tile():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    assert world.get_tile(x, surface_y) == GRASS_ID
    projectile = Projectile(x * TILE_SIZE, surface_y * TILE_SIZE, 0.0, 0.0, damage=1.0)
    survivors = combat_system.update_projectiles([projectile], world, [], dt=1 / 60)
    assert survivors == []


# --- contact damage / invulnerability ---

def test_contact_damage_applies_once_then_respects_invulnerability():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = _make_player_at(world, x)
    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)

    starting_hp = player.health
    combat_system.resolve_contact_damage(player, [enemy])
    assert player.health == starting_hp - enemy.enemy_def.contact_damage
    assert player.is_invulnerable() is True

    combat_system.resolve_contact_damage(player, [enemy])  # still overlapping
    assert player.health == starting_hp - enemy.enemy_def.contact_damage  # unchanged


def test_enemy_invulnerability_blocks_repeat_damage():
    enemy = Enemy(enemy_registry.get("slime"), 0, 0)
    assert enemy.take_damage(5.0) is True
    assert enemy.take_damage(5.0) is False  # still in i-frames
    assert enemy.health == enemy.enemy_def.max_health - 5.0


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
        assert len(enemies) <= ENEMY_MAX_ALIVE


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
