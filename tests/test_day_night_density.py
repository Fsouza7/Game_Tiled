"""Headless tests for the day/night + underground mob-density system
(game/entities/enemy_spawner.py): fewer/slower spawns in daylight, more/
faster at night, and the most dangerous of all once the player is deep
enough underground -- regardless of the surface day/night cycle, since
caves are already dark either way (see "How lighting works").
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    ENEMY_MAX_ALIVE_DAY, ENEMY_MAX_ALIVE_NIGHT, ENEMY_MAX_ALIVE_UNDERGROUND,
    ENEMY_SPAWN_INTERVAL_DAY_S, ENEMY_SPAWN_INTERVAL_NIGHT_S, ENEMY_SPAWN_INTERVAL_UNDERGROUND_S,
    UNDERGROUND_SPAWN_DEPTH_TILES,
)
from game.entities import enemy_registry
from game.entities.enemy_def import AIType
from game.entities.enemy_spawner import (
    EnemySpawner, UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES, _underground_spawn_y_tiles,
)
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import AIR_ID, STONE_ID


def _make_player_at(world, x_tile, y_tile=None):
    if y_tile is None:
        surface_y = world.surface_spawn_y(x_tile) + 1
        y_tile = surface_y - 1
    return Player(x_tile * TILE_SIZE, y_tile * TILE_SIZE)


# --- _current_limits ---

def test_current_limits_day_vs_night_at_the_surface():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    spawner = EnemySpawner()

    assert spawner._current_limits(world, player, is_night=False) == (
        ENEMY_MAX_ALIVE_DAY, ENEMY_SPAWN_INTERVAL_DAY_S, False,
    )
    assert spawner._current_limits(world, player, is_night=True) == (
        ENEMY_MAX_ALIVE_NIGHT, ENEMY_SPAWN_INTERVAL_NIGHT_S, False,
    )


def test_current_limits_underground_overrides_day_and_night():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    deep_player = _make_player_at(world, x, surface_y + UNDERGROUND_SPAWN_DEPTH_TILES + 5)
    spawner = EnemySpawner()

    assert spawner._current_limits(world, deep_player, is_night=False) == (
        ENEMY_MAX_ALIVE_UNDERGROUND, ENEMY_SPAWN_INTERVAL_UNDERGROUND_S, True,
    )
    assert spawner._current_limits(world, deep_player, is_night=True) == (
        ENEMY_MAX_ALIVE_UNDERGROUND, ENEMY_SPAWN_INTERVAL_UNDERGROUND_S, True,
    )


def test_a_shallow_dip_does_not_count_as_underground():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    shallow_player = _make_player_at(world, x, surface_y + UNDERGROUND_SPAWN_DEPTH_TILES - 1)
    spawner = EnemySpawner()

    _, _, underground = spawner._current_limits(world, shallow_player, is_night=False)
    assert underground is False


# --- _underground_spawn_y_tiles ---

def test_underground_spawn_finds_a_carved_cave_floor_near_player_depth():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    deep_y = surface_y + 30
    world.set_tile(x, deep_y - 2, AIR_ID)
    world.set_tile(x, deep_y - 1, AIR_ID)
    world.set_tile(x, deep_y, AIR_ID)
    world.set_tile(x, deep_y + 1, STONE_ID)  # solid floor directly beneath

    ground_def = enemy_registry.get("crawler")
    spawn_y = _underground_spawn_y_tiles(world, x, float(deep_y), ground_def)
    assert spawn_y == deep_y
    assert not world.is_solid(x, spawn_y)
    assert world.is_solid(x, spawn_y + 1)


def test_underground_spawn_returns_none_in_solid_rock_with_no_opening():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    deep_y = surface_y + 30
    for y in range(deep_y - UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES, deep_y + UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES + 1):
        world.set_tile(x, y, STONE_ID)

    ground_def = enemy_registry.get("crawler")
    assert _underground_spawn_y_tiles(world, x, float(deep_y), ground_def) is None


def test_underground_spawn_a_flyer_only_needs_open_air_not_a_floor():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    deep_y = surface_y + 30
    for y in range(deep_y - UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES, deep_y + UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES + 1):
        world.set_tile(x, y, STONE_ID)
    world.set_tile(x, deep_y, AIR_ID)  # a single open cell, no floor beneath it

    flyer_def = next(e for e in enemy_registry.all_enemies() if e.ai_type == AIType.FLY)
    assert _underground_spawn_y_tiles(world, x, float(deep_y), flyer_def) == deep_y


# --- full spawn loop respects the right cap per situation ---

def test_spawner_respects_the_day_cap_at_the_surface():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    spawner = EnemySpawner()
    enemies = []

    for _ in range(2000):
        spawner.time_until_next_spawn = 0.0
        spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
        enemies = [e for e in enemies if e.alive]
        assert len(enemies) <= ENEMY_MAX_ALIVE_DAY


def test_spawner_respects_the_night_cap_at_the_surface():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    spawner = EnemySpawner()
    enemies = []

    for _ in range(2000):
        spawner.time_until_next_spawn = 0.0
        spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=True)
        enemies = [e for e in enemies if e.alive]
        assert len(enemies) <= ENEMY_MAX_ALIVE_NIGHT
    assert len(enemies) > ENEMY_MAX_ALIVE_DAY  # actually denser than the day cap, not just "under some cap"


def test_spawner_respects_the_underground_cap_and_spawns_at_depth():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    deep_y = surface_y + UNDERGROUND_SPAWN_DEPTH_TILES + 10
    # A long carved tunnel across the whole spawn-distance range so random
    # spawn attempts reliably find an opening near the player's own depth.
    for cx in range(x - 40, x + 41):
        world.set_tile(cx, deep_y - 1, AIR_ID)
        world.set_tile(cx, deep_y, AIR_ID)
        world.set_tile(cx, deep_y + 1, STONE_ID)

    player = _make_player_at(world, x, deep_y)
    spawner = EnemySpawner()
    enemies = []

    for _ in range(3000):
        spawner.time_until_next_spawn = 0.0
        spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
        enemies = [e for e in enemies if e.alive]
        assert len(enemies) <= ENEMY_MAX_ALIVE_UNDERGROUND

    assert len(enemies) > 0  # the carved tunnel actually got used, not a trivial empty pass
    for enemy in enemies:
        # Spawned near the player's own depth, not up at the world surface.
        assert abs(enemy.center_y / TILE_SIZE - deep_y) < UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES + 2
