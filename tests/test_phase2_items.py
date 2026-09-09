"""Headless tests for the Phase 2 data-driven item system: category
coverage, schema fields, and the one new fully-functional item
(wooden_crate) end to end (world spawn -> mine -> place).
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE
from game.items.item import ItemCategory
from game.items import item_registry
from game.entities.player import Player
from game.world.world import World
from game.world import tile_registry
from game.world.tile_registry import DECOR_CRATE_ID
from game.world.world_generator import CRATE_SPAWN_CHANCE


def test_every_category_has_at_least_one_item():
    present = {item.category for item in item_registry.all_items().values()}
    assert present == set(ItemCategory)


def test_icon_tile_id_always_points_to_a_real_tile():
    for item in item_registry.all_items().values():
        if item.icon_tile_id is not None:
            tile_registry.get(item.icon_tile_id)  # raises KeyError if invalid
        if item.places_tile_id is not None:
            tile_registry.get(item.places_tile_id)


def test_ore_items_use_their_own_tile_texture_as_icon():
    # Regression check for the "flat gray swatch" bug: ore items must not
    # fall through to the generic category swatch.
    assert item_registry.get("coal").icon_tile_id == tile_registry.COAL_ORE_ID
    assert item_registry.get("iron_ore").icon_tile_id == tile_registry.IRON_ORE_ID
    assert item_registry.get("wood").icon_tile_id == tile_registry.TREE_TRUNK_ID


def test_by_category_helper_filters_correctly():
    tools = item_registry.by_category(ItemCategory.TOOL)
    assert "wood_pickaxe" in tools
    assert all(item.category == ItemCategory.TOOL for item in tools.values())


def test_wood_pickaxe_schema_fields():
    item = item_registry.get("wood_pickaxe")
    assert item.is_tool is True
    assert item.tool_type == "pickaxe"
    assert item.max_durability == 60
    assert item.category == ItemCategory.TOOL


def test_weapon_schema_has_damage_and_speed():
    sword = item_registry.get("wood_sword")
    assert sword.category == ItemCategory.WEAPON
    assert sword.damage > 0
    assert sword.speed > 0
    assert sword.max_durability is not None


def test_only_the_starter_pickaxe_is_granted_by_default():
    # Everything else (materials, weapons, armor, consumables) must be
    # gathered/crafted -- confirm none of it is silently handed to the
    # player as a shortcut, even once it's obtainable elsewhere.
    player = Player(0, 0)
    for item_id in ("wood", "wood_sword", "wood_helmet", "wood_armor", "apple"):
        assert player.inventory.count_item(item_id) == 0
    assert player.inventory.count_item("wood_pickaxe") == 1


def test_no_duplicate_item_ids():
    ids = list(item_registry.all_items().keys())
    assert len(ids) == len(set(ids))


# --- wooden_crate: the one Decoration-category item that's actually
# obtainable in Phase 2, exercised end to end. ---

def _find_crate_column(world: World) -> int:
    for x in range(WORLD_WIDTH_TILES):
        surface_y = world.surface_spawn_y(x) + 1
        if world.get_tile(x, surface_y - 1) == DECOR_CRATE_ID:
            return x
    raise AssertionError("no crate spawned anywhere in the world -- check CRATE_SPAWN_CHANCE/seed")


def test_crate_decoration_spawns_deterministically():
    assert 0 < CRATE_SPAWN_CHANCE < 0.1  # sanity: rare, but not effectively zero
    world = World(DEFAULT_SEED)
    x = _find_crate_column(world)  # raises if none found
    # same seed -> same spawn column
    world_b = World(DEFAULT_SEED)
    surface_y = world_b.surface_spawn_y(x) + 1
    assert world_b.get_tile(x, surface_y - 1) == DECOR_CRATE_ID


def test_mine_and_place_wooden_crate():
    world = World(DEFAULT_SEED)
    x = _find_crate_column(world)
    surface_y = world.surface_spawn_y(x) + 1
    crate_y = surface_y - 1

    player = Player(x * TILE_SIZE, crate_y * TILE_SIZE)
    drop = None
    for _ in range(50):
        drop = player.try_mine(world, x, crate_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "wooden_crate"
    assert world.get_tile(x, crate_y) != DECOR_CRATE_ID

    placed = world.try_place_tile(x, crate_y, DECOR_CRATE_ID)  # same hole has adjacent support
    assert placed is True
    assert world.get_tile(x, crate_y) == DECOR_CRATE_ID
