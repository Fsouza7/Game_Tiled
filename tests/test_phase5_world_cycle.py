"""Headless tests for Phase 5: the day/night clock, torch-based lighting
(computed only for a bounded viewport, never the whole world), the torch
item/tile/recipe, and night-exclusive enemy spawning.
"""
import random

import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, DAY_LENGTH_S,
    NIGHT_MIN_AMBIENT, DAY_MAX_AMBIENT, LIGHT_RADIUS_TILES,
)
from game.core.world_clock import WorldClock
from game.world import lighting
from game.world.world import World
from game.world.tile_registry import TORCH_ID, AIR_ID
from game.items import item_registry
from game.crafting import recipe_registry
from game.entities.enemy_registry import get as get_enemy_def, all_enemies
from game.entities.enemy_def import SpawnTime
from game.entities.enemy_spawner import EnemySpawner
from game.entities.player import Player


# --- WorldClock ---

def test_clock_wraps_around_and_counts_days():
    clock = WorldClock()
    clock.time_of_day = DAY_LENGTH_S - 1.0
    start_day = clock.day_count
    clock.update(2.0)
    assert clock.day_count == start_day + 1
    assert 0.0 <= clock.time_of_day < DAY_LENGTH_S


def test_ambient_light_is_darkest_at_midnight_brightest_at_noon():
    clock = WorldClock()
    clock.time_of_day = 0.0  # midnight
    midnight_ambient = clock.ambient_light
    clock.time_of_day = DAY_LENGTH_S * 0.5  # noon
    noon_ambient = clock.ambient_light

    assert abs(midnight_ambient - NIGHT_MIN_AMBIENT) < 1e-6
    assert abs(noon_ambient - DAY_MAX_AMBIENT) < 1e-6
    assert noon_ambient > midnight_ambient


def test_ambient_light_transitions_smoothly_not_in_jumps():
    clock = WorldClock()
    samples = []
    for i in range(200):
        clock.time_of_day = DAY_LENGTH_S * (i / 200.0)
        samples.append(clock.ambient_light)
    # No single step between consecutive samples should be a big jump --
    # confirms the cosine curve, not a discrete day/night switch.
    max_step = max(abs(samples[i + 1] - samples[i]) for i in range(len(samples) - 1))
    assert max_step < 0.05


def test_is_night_matches_the_ambient_threshold():
    clock = WorldClock()
    clock.time_of_day = 0.0
    assert clock.is_night is True
    clock.time_of_day = DAY_LENGTH_S * 0.5
    assert clock.is_night is False


def test_clock_string_is_a_plausible_24h_time():
    clock = WorldClock()
    clock.time_of_day = 0.0
    assert clock.clock_string() == "00:00"
    clock.time_of_day = DAY_LENGTH_S * 0.5
    assert clock.clock_string() == "12:00"


# --- Lighting ---

def test_light_level_far_from_any_source_is_just_ambient():
    world = World(DEFAULT_SEED)
    level = lighting.light_level_at(0.0, 0.0, light_sources=[], ambient_light=0.3)
    assert level == 0.3


def test_light_level_near_a_bright_source_approaches_full_brightness():
    sources = [(10, 10, 1.0)]
    level = lighting.light_level_at(10, 10, sources, ambient_light=0.1)
    assert level > 0.9


def test_light_level_falls_off_with_distance():
    sources = [(0, 0, 1.0)]
    near = lighting.light_level_at(1, 0, sources, ambient_light=0.0)
    far = lighting.light_level_at(5, 0, sources, ambient_light=0.0)
    assert near > far > 0.0


def test_light_level_beyond_radius_is_pure_ambient():
    sources = [(0, 0, 1.0)]
    beyond = LIGHT_RADIUS_TILES + 1
    level = lighting.light_level_at(beyond, 0, sources, ambient_light=0.2)
    assert level == 0.2


def test_light_never_exceeds_1():
    sources = [(0, 0, 1.0), (0, 0, 1.0)]
    level = lighting.light_level_at(0, 0, sources, ambient_light=0.9)
    assert level <= 1.0


def test_ambient_light_for_depth_unchanged_at_and_above_the_surface():
    for depth in (0, -1, -5):
        assert lighting.ambient_light_for_depth(depth, sky_ambient=0.8) == 0.8


def test_ambient_light_for_depth_fades_out_underground_even_at_noon():
    from game.settings import UNDERGROUND_MIN_AMBIENT, UNDERGROUND_DARK_DEPTH_TILES
    shallow = lighting.ambient_light_for_depth(1.0, sky_ambient=DAY_MAX_AMBIENT)
    deep = lighting.ambient_light_for_depth(UNDERGROUND_DARK_DEPTH_TILES * 2, sky_ambient=DAY_MAX_AMBIENT)
    assert DAY_MAX_AMBIENT > shallow > deep
    assert deep == UNDERGROUND_MIN_AMBIENT  # floored, never pitch black


def test_ambient_light_for_depth_never_goes_below_the_floor_even_at_night():
    from game.settings import UNDERGROUND_MIN_AMBIENT
    level = lighting.ambient_light_for_depth(1000.0, sky_ambient=NIGHT_MIN_AMBIENT)
    assert level == UNDERGROUND_MIN_AMBIENT


def test_world_surface_height_at_matches_surface_spawn_y():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    assert world.surface_height_at(x) - 1 == world.surface_spawn_y(x)


def test_find_light_sources_only_within_given_bounds():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    torch_y = surface_y - 1
    placed = world.try_place_tile(x, torch_y, TORCH_ID)
    assert placed

    inside = lighting.find_light_sources(world, x - 2, x + 2, torch_y - 2, torch_y + 2)
    assert any(sx == x and sy == torch_y for sx, sy, _ in inside)

    outside = lighting.find_light_sources(world, x + 50, x + 55, torch_y, torch_y)
    assert outside == []


# --- Torch item/tile/recipe ---

def test_torch_tile_emits_light_and_is_fragile():
    from game.world import tile_registry
    torch_def = tile_registry.get(TORCH_ID)
    assert torch_def.light_emit > 0
    assert torch_def.can_place and torch_def.can_break
    assert torch_def.solid is False  # doesn't block movement


def test_torch_item_and_recipe_are_registered():
    torch_item = item_registry.get("torch")
    assert torch_item.places_tile_id == TORCH_ID
    recipe = recipe_registry.get("torch")
    item_registry.get(recipe.result_item_id)
    for item_id, qty in recipe.ingredients:
        item_registry.get(item_id)
        assert qty > 0


def test_mine_and_place_torch():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    torch_y = surface_y - 1
    assert world.try_place_tile(x, torch_y, TORCH_ID)

    player = Player(x * TILE_SIZE, torch_y * TILE_SIZE)
    drop = None
    for _ in range(50):
        drop = player.try_mine(world, x, torch_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "torch"
    assert world.get_tile(x, torch_y) == AIR_ID


# --- Night-exclusive spawning ---

def test_duskwing_is_night_only():
    duskwing = get_enemy_def("duskwing")
    assert duskwing.spawn_time == SpawnTime.NIGHT


def test_other_enemies_spawn_any_time():
    for enemy_id in ("slime", "crawler"):
        assert get_enemy_def(enemy_id).spawn_time == SpawnTime.ANY


def test_spawner_never_picks_duskwing_during_the_day():
    random.seed(1)
    spawner = EnemySpawner()
    for _ in range(300):
        picked = spawner._pick_weighted_enemy(is_night=False)
        assert picked is not None
        assert picked.id != "duskwing"


def test_spawner_can_pick_duskwing_at_night():
    random.seed(1)
    spawner = EnemySpawner()
    picks = {spawner._pick_weighted_enemy(is_night=True).id for _ in range(300)}
    assert "duskwing" in picks
    assert "slime" in picks or "crawler" in picks  # ANY-time enemies still eligible


def test_spawner_time_filter_never_returns_none_given_current_roster():
    # Sanity: with the current enemy roster, every time-of-day has at least
    # one eligible enemy (slime/crawler are ANY), so spawning never silently
    # stalls just because it's day or night.
    spawner = EnemySpawner()
    assert spawner._pick_weighted_enemy(is_night=True) is not None
    assert spawner._pick_weighted_enemy(is_night=False) is not None
