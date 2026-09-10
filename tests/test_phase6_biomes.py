"""Headless tests for Phase 6: biome zoning (deterministic, seed-consistent,
always-Forest spawn), per-biome ground tiles/vegetation/resources, per-biome
underground stone/ores, and the desert-exclusive enemy.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, TILE_SIZE,
    BIOME_ZONE_WIDTH_TILES, ORE_MIN_DEPTH_BELOW_SURFACE, BEDROCK_ROWS,
)
from game.world import biome_registry
from game.world.biome_registry import FOREST_ID, DESERT_ID, SNOW_ID, JUNGLE_ID
from game.world.world import World
from game.world.world_generator import biome_at, generate_column
from game.world.tile_registry import (
    GRASS_ID, DIRT_ID, SAND_ID, SANDSTONE_ID, SNOW_BLOCK_ID, FROZEN_DIRT_ID,
    JUNGLE_GRASS_ID, MUD_ID, CACTUS_ID, TREE_ID, AIR_ID, STONE_ID,
    DESERT_STONE_ID, SNOW_STONE_ID, JUNGLE_STONE_ID,
    TOPAZ_ORE_ID, SAPPHIRE_ORE_ID, EMERALD_ORE_ID,
    COAL_ORE_ID, IRON_ORE_ID,
    SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID, FAN_ID,
    WOOD_PLANK_ID, TORCH_ID, CHEST_ID,
)
from game.items import item_registry
from game.crafting import recipe_registry
from game.entities.enemy_registry import get as get_enemy_def
from game.entities.enemy_spawner import EnemySpawner
from game.entities.player import Player


# --- Biome zoning ---

def test_spawn_point_is_always_forest():
    biome = biome_at(DEFAULT_SEED, WORLD_WIDTH_TILES // 2)
    assert biome.id == FOREST_ID


def test_spawn_safety_window_is_forest_on_both_sides():
    spawn_x = WORLD_WIDTH_TILES // 2
    half_window = BIOME_ZONE_WIDTH_TILES // 2
    for offset in (-half_window + 1, 0, half_window - 1):
        assert biome_at(DEFAULT_SEED, spawn_x + offset).id == FOREST_ID


def test_biome_is_deterministic_for_same_seed():
    for x in (0, 500, 1234, WORLD_WIDTH_TILES - 1):
        assert biome_at(DEFAULT_SEED, x).id == biome_at(DEFAULT_SEED, x).id


def test_different_seeds_can_produce_different_biome_layouts():
    # Not guaranteed for every single x, but across many far-from-spawn
    # columns two different seeds should disagree at least once.
    far_columns = range(0, 800, 17)
    differs = any(
        biome_at(DEFAULT_SEED, x).id != biome_at(DEFAULT_SEED + 1, x).id
        for x in far_columns
    )
    assert differs


def test_all_four_biomes_appear_somewhere_in_the_world():
    seen = {biome_at(DEFAULT_SEED, x).id for x in range(0, WORLD_WIDTH_TILES, 23)}
    assert seen == {FOREST_ID, DESERT_ID, SNOW_ID, JUNGLE_ID}


# --- Per-biome tiles ---

def test_forest_column_uses_grass_and_dirt():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    assert world.get_tile(x, surface_y) == GRASS_ID
    assert world.get_tile(x, surface_y + 2) == DIRT_ID


def _find_column_in_biome(seed, biome_id, search_range=range(0, WORLD_WIDTH_TILES, 5)):
    for x in search_range:
        if biome_at(seed, x).id == biome_id:
            return x
    raise AssertionError(f"no column found in biome {biome_id}")


def test_desert_column_uses_sand_and_sandstone():
    x = _find_column_in_biome(DEFAULT_SEED, DESERT_ID)
    column = generate_column(DEFAULT_SEED, x)
    from game.world.world_generator import surface_height
    surface_y = surface_height(DEFAULT_SEED, x)
    assert column[surface_y] == SAND_ID
    assert column[surface_y + 2] == SANDSTONE_ID


def test_snow_column_uses_snow_and_frozen_dirt():
    x = _find_column_in_biome(DEFAULT_SEED, SNOW_ID)
    column = generate_column(DEFAULT_SEED, x)
    from game.world.world_generator import surface_height
    surface_y = surface_height(DEFAULT_SEED, x)
    assert column[surface_y] == SNOW_BLOCK_ID
    assert column[surface_y + 2] == FROZEN_DIRT_ID


def test_jungle_column_uses_jungle_grass_and_mud():
    x = _find_column_in_biome(DEFAULT_SEED, JUNGLE_ID)
    column = generate_column(DEFAULT_SEED, x)
    from game.world.world_generator import surface_height
    surface_y = surface_height(DEFAULT_SEED, x)
    assert column[surface_y] == JUNGLE_GRASS_ID
    assert column[surface_y + 2] == MUD_ID


# --- Per-biome underground (stone + exclusive ore) ---

def _underground_tiles_in_biome(seed, biome_id, x_range=range(0, WORLD_WIDTH_TILES, 4)):
    """All distinct tile ids found in the ore-eligible underground band
    (below the dirt layer, above bedrock -- may include cave AIR_ID) across
    every column belonging to the given biome."""
    from game.world.world_generator import surface_height
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS
    found = set()
    for x in x_range:
        if biome_at(seed, x).id != biome_id:
            continue
        surface_y = surface_height(seed, x)
        column = generate_column(seed, x)
        for y in range(surface_y + ORE_MIN_DEPTH_BELOW_SURFACE, bedrock_start_y):
            found.add(column[y])
    return found


# Static cave-floor hazards (Spikes/Fire/Arrow Trap/Falling Platform) and
# Fan shafts are generated from the same shared noise field as caves
# themselves, so they can legitimately turn up underground in any biome
# (see world_generator._place_cave_hazard / _place_fan_shaft). An
# Underground Room (Phase 7, see game/world/structures.py) can too --
# WOOD_PLANK_ID/TORCH_ID/CHEST_ID are the same regardless of biome, and its
# walls are built from that column's own biome underground_tile_id (so
# STONE_ID here is still Forest-only, same as before).
_CAVE_HAZARDS = {
    SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID, FAN_ID,
    WOOD_PLANK_ID, TORCH_ID, CHEST_ID,
}


def test_forest_underground_uses_stone_and_no_exclusive_gem():
    tiles = _underground_tiles_in_biome(DEFAULT_SEED, FOREST_ID)
    assert STONE_ID in tiles
    assert tiles <= {AIR_ID, STONE_ID, COAL_ORE_ID, IRON_ORE_ID} | _CAVE_HAZARDS


def test_desert_underground_uses_desert_stone_and_topaz():
    tiles = _underground_tiles_in_biome(DEFAULT_SEED, DESERT_ID)
    assert DESERT_STONE_ID in tiles
    assert TOPAZ_ORE_ID in tiles
    assert tiles <= {AIR_ID, DESERT_STONE_ID, COAL_ORE_ID, IRON_ORE_ID, TOPAZ_ORE_ID} | _CAVE_HAZARDS
    assert STONE_ID not in tiles and SNOW_STONE_ID not in tiles and JUNGLE_STONE_ID not in tiles


def test_snow_underground_uses_permafrost_stone_and_sapphire():
    tiles = _underground_tiles_in_biome(DEFAULT_SEED, SNOW_ID)
    assert SNOW_STONE_ID in tiles
    assert SAPPHIRE_ORE_ID in tiles
    assert tiles <= {AIR_ID, SNOW_STONE_ID, COAL_ORE_ID, IRON_ORE_ID, SAPPHIRE_ORE_ID} | _CAVE_HAZARDS
    assert STONE_ID not in tiles


def test_jungle_underground_uses_jungle_stone_and_emerald():
    tiles = _underground_tiles_in_biome(DEFAULT_SEED, JUNGLE_ID)
    assert JUNGLE_STONE_ID in tiles
    assert EMERALD_ORE_ID in tiles
    assert tiles <= {AIR_ID, JUNGLE_STONE_ID, COAL_ORE_ID, IRON_ORE_ID, EMERALD_ORE_ID} | _CAVE_HAZARDS
    assert STONE_ID not in tiles


def test_mine_topaz_for_the_gem_item():
    world = World(DEFAULT_SEED)
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS
    ore_x = ore_y = None
    for x in range(0, WORLD_WIDTH_TILES, 3):
        if biome_at(DEFAULT_SEED, x).id != DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        for y in range(surface_y + ORE_MIN_DEPTH_BELOW_SURFACE, bedrock_start_y):
            if world.get_tile(x, y) == TOPAZ_ORE_ID:
                ore_x, ore_y = x, y
                break
        if ore_x is not None:
            break
    assert ore_x is not None, "no topaz ore found to test mining"

    player = Player(ore_x * TILE_SIZE, ore_y * TILE_SIZE)
    drop = None
    for _ in range(50):
        drop = player.try_mine(world, ore_x, ore_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "topaz"
    assert world.get_tile(ore_x, ore_y) == AIR_ID


def test_biome_stone_and_gem_items_are_registered():
    for item_id, tile_id in (
        ("desert_stone_block", DESERT_STONE_ID), ("snow_stone_block", SNOW_STONE_ID),
        ("jungle_stone_block", JUNGLE_STONE_ID),
    ):
        assert item_registry.get(item_id).places_tile_id == tile_id
    # The three gems use a dedicated loose-ore-chunk icon from the
    # user-supplied icon sheet (icon_key, see assets._SHEET_ICON_CELLS)
    # rather than their own tile's texture -- see item_registry.py.
    for item_id in ("topaz", "sapphire", "emerald"):
        assert item_registry.get(item_id).icon_key == item_id


# --- Desert vegetation: cacti instead of trees ---

def test_desert_has_no_trees():
    world = World(DEFAULT_SEED)
    for x in range(0, WORLD_WIDTH_TILES, 3):
        if biome_at(DEFAULT_SEED, x).id != DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        for dy in range(1, 6):
            assert world.get_tile(x, surface_y - dy) != TREE_ID


def test_desert_spawns_cacti():
    world = World(DEFAULT_SEED)
    found = False
    for x in range(0, WORLD_WIDTH_TILES):
        if biome_at(DEFAULT_SEED, x).id != DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        if world.get_tile(x, surface_y - 1) == CACTUS_ID:
            found = True
            break
    assert found


def test_mine_a_cactus_for_cactus_fiber():
    world = World(DEFAULT_SEED)
    cactus_x = cactus_y = None
    for x in range(0, WORLD_WIDTH_TILES):
        if biome_at(DEFAULT_SEED, x).id != DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        if world.get_tile(x, surface_y - 1) == CACTUS_ID:
            cactus_x, cactus_y = x, surface_y - 1
            break
    assert cactus_x is not None, "no cactus found to test mining"

    player = Player(cactus_x * TILE_SIZE, cactus_y * TILE_SIZE)
    drop = None
    for _ in range(50):
        drop = player.try_mine(world, cactus_x, cactus_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "cactus_fiber"
    assert world.get_tile(cactus_x, cactus_y) == AIR_ID


# --- Items / recipes ---

def test_biome_block_items_reference_real_tiles():
    for item_id, tile_id in (
        ("sand_block", SAND_ID), ("sandstone_block", SANDSTONE_ID),
        ("snow_block", SNOW_BLOCK_ID), ("frozen_dirt_block", FROZEN_DIRT_ID),
        ("jungle_grass_block", JUNGLE_GRASS_ID), ("mud_block", MUD_ID),
    ):
        assert item_registry.get(item_id).places_tile_id == tile_id


def test_cactus_arrow_recipe_is_registered():
    recipe = recipe_registry.get("arrow_cactus")
    assert recipe.result_item_id == "arrow"
    assert recipe.ingredients == (("cactus_fiber", 2),)


# --- Scorpion: biome-gated enemy ---

def test_scorpion_is_desert_only():
    scorpion = get_enemy_def("scorpion")
    assert scorpion.biome_id == DESERT_ID


def test_spawner_never_picks_scorpion_outside_its_biome():
    spawner = EnemySpawner()
    for _ in range(300):
        picked = spawner._pick_weighted_enemy(is_night=False, biome_id=FOREST_ID)
        assert picked.id != "scorpion"


def test_spawner_can_pick_scorpion_in_the_desert():
    spawner = EnemySpawner()
    picks = {spawner._pick_weighted_enemy(is_night=False, biome_id=DESERT_ID).id for _ in range(300)}
    assert "scorpion" in picks


def test_spawner_default_biome_excludes_biome_gated_enemies():
    # Calling without a biome_id (e.g. existing day/night-only tests) should
    # keep behaving as "no specific biome" -- Scorpion never appears.
    spawner = EnemySpawner()
    for _ in range(200):
        picked = spawner._pick_weighted_enemy(is_night=False)
        assert picked.id != "scorpion"
