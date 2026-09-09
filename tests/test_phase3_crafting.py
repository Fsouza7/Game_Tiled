"""Headless tests for Phase 3 crafting: recipe registry, ingredient/station
gating, the actual craft() transaction, and the trees that make the "wood"
ingredient obtainable.
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE
from game.crafting import recipe_registry, crafting_system
from game.items import item_registry
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import WORKBENCH_ID, TREE_TRUNK_ID, TREE_LEAVES_ID, AIR_ID


def _find_trunk_position(world: World):
    for x in range(WORLD_WIDTH_TILES):
        surface_y = world.surface_spawn_y(x) + 1
        for dy in range(1, 6):
            y = surface_y - dy
            if world.get_tile(x, y) == TREE_TRUNK_ID:
                return x, y
    raise AssertionError("no tree trunk ever spawned -- check TREE_SPAWN_CHANCE_PER_SLOT/seed")


def _find_clear_air_column(world: World, near_x: int, search_radius: int = 40) -> int:
    """A column whose (surface_y - 1) tile is plain air -- i.e. no tree/crate
    already sitting there -- so a workbench can be placed without depending
    on exactly where trees landed for this seed."""
    for offset in range(search_radius):
        for x in (near_x + offset, near_x - offset):
            if 0 <= x < WORLD_WIDTH_TILES:
                surface_y = world.surface_spawn_y(x) + 1
                if world.get_tile(x, surface_y - 1) == AIR_ID:
                    return x
    raise AssertionError("no clear surface column found near_x for placing a workbench")


def _mine_until_dropped(player, world, x, y, max_ticks=200):
    for _ in range(max_ticks):
        drop = player.try_mine(world, x, y, dt=0.1)
        if drop is not None:
            return drop
    return None


# --- registry sanity ---

def test_recipes_reference_real_items():
    from game.items import item_registry
    for recipe in recipe_registry.all_recipes():
        item_registry.get(recipe.result_item_id)  # raises if missing
        for item_id, qty in recipe.ingredients:
            item_registry.get(item_id)
            assert qty > 0


def test_workbench_recipe_has_no_station_requirement():
    recipe = recipe_registry.get("workbench")
    assert recipe.station_tile_id is None
    assert recipe.ingredients == (("wood", 10),)


def test_stone_pickaxe_recipe_requires_workbench():
    recipe = recipe_registry.get("stone_pickaxe")
    assert recipe.station_tile_id == WORKBENCH_ID


def test_wood_plank_recipe_yields_four_per_wood():
    recipe = recipe_registry.get("wood_plank_block")
    assert recipe.ingredients == (("wood", 1),)
    assert recipe.result_quantity == 4
    assert recipe.station_tile_id is None


def test_wood_pickaxe_remake_recipe_has_no_station():
    recipe = recipe_registry.get("wood_pickaxe")
    assert recipe.station_tile_id is None


# --- tree / wood obtainability ---

def test_tree_trunk_spawns_and_is_choppable():
    world = World(DEFAULT_SEED)
    x, y = _find_trunk_position(world)

    player = Player(x * TILE_SIZE, y * TILE_SIZE)
    drop = _mine_until_dropped(player, world, x, y)
    assert drop == "wood"


def test_tree_has_a_canopy_next_to_the_trunk():
    world = World(DEFAULT_SEED)
    x, y = _find_trunk_position(world)
    # The trunk's top few rows should have leaves directly above, and at
    # least one neighboring column should carry canopy too (a real 3-wide
    # tree, not a single floating tile).
    surface_y = world.surface_spawn_y(x) + 1
    canopy_y = surface_y - 4
    assert world.get_tile(x, canopy_y) == TREE_LEAVES_ID
    assert (
        world.get_tile(x - 1, canopy_y) == TREE_LEAVES_ID
        or world.get_tile(x + 1, canopy_y) == TREE_LEAVES_ID
    )


# --- crafting rules ---

def test_cannot_craft_without_enough_ingredients():
    world = World(DEFAULT_SEED)
    player = Player(0, 0)
    recipe = recipe_registry.get("workbench")
    assert player.inventory.count_item("wood") == 0
    assert not crafting_system.can_craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert not crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y)


def test_craft_workbench_consumes_wood_and_grants_item():
    world = World(DEFAULT_SEED)
    player = Player(0, 0)
    player.inventory.add_item("wood", 10)

    recipe = recipe_registry.get("workbench")
    assert crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert player.inventory.count_item("wood") == 0
    assert player.inventory.count_item("workbench") == 1


def test_stone_pickaxe_requires_being_near_a_placed_workbench():
    world = World(DEFAULT_SEED)
    x = _find_clear_air_column(world, WORLD_WIDTH_TILES // 2)
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    player.inventory.add_item("wood", 5)
    player.inventory.add_item("stone_block", 10)

    recipe = recipe_registry.get("stone_pickaxe")
    # far from any workbench: ingredients present, but station missing
    assert crafting_system.has_ingredients(recipe, player.inventory)
    assert not crafting_system.can_craft(recipe, player.inventory, world, player.center_x, player.center_y)

    placed = world.try_place_tile(x, surface_y - 1, WORKBENCH_ID)
    assert placed
    assert crafting_system.can_craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert player.inventory.count_item("stone_pickaxe") == 1
    assert player.inventory.count_item("wood") == 0
    assert player.inventory.count_item("stone_block") == 0


def test_craft_refunds_ingredients_if_inventory_is_full():
    world = World(DEFAULT_SEED)
    player = Player(0, 0)
    # More than the recipe needs, so consuming the ingredient doesn't itself
    # free up the slot it lives in.
    player.inventory.add_item("wood", 15)

    for slot in player.inventory.slots:
        if slot.is_empty:
            slot.item_id = "stone_block"
            slot.quantity = 99

    recipe = recipe_registry.get("workbench")
    result = crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert result is False
    assert player.inventory.count_item("wood") == 15  # fully refunded, not lost
    assert player.inventory.count_item("workbench") == 0


# --- crafting screen: sectioning, discovery visibility and scroll ---

def _every_item_id():
    return set(item_registry.all_items().keys())


def test_undiscovered_recipes_are_left_out_of_every_section():
    from game.rendering.renderer import _recipe_sections

    sections_nothing_discovered = _recipe_sections(discovered_item_ids=set())
    # Nothing has ever been picked up -- every section is empty, so none appear.
    assert sections_nothing_discovered == []

    sections_everything_discovered = _recipe_sections(discovered_item_ids=_every_item_id())
    assert sum(len(recipes) for _, recipes in sections_everything_discovered) > 0


def test_recipes_are_grouped_by_result_category_with_a_trailing_smelting_section():
    from game.rendering.renderer import _recipe_sections, _CATEGORY_SECTION_ORDER
    from game.crafting import smelt_registry

    title_to_category = {title: category for category, title in _CATEGORY_SECTION_ORDER}
    sections = _recipe_sections(discovered_item_ids=_every_item_id())

    assert sections[-1][0] == "Smelting (Furnace)"
    assert {r.id for r in sections[-1][1]} == {r.id for r in smelt_registry.all_recipes()}

    for title, recipes in sections[:-1]:
        expected_category = title_to_category[title]
        for recipe in recipes:
            assert item_registry.get(recipe.result_item_id).category == expected_category

    # With every ingredient discovered, every registered recipe (crafting +
    # smelting) appears in exactly one section.
    total_in_sections = sum(len(recipes) for _, recipes in sections)
    assert total_in_sections == len(recipe_registry.all_recipes()) + len(smelt_registry.all_recipes())


def test_crafting_scroll_clamps_and_click_hit_test_respects_it():
    from game.rendering.renderer import (
        crafting_max_scroll, crafting_panel_height, recipe_at_screen_pos, _crafting_layout,
        CRAFTING_PANEL_X, CRAFTING_PANEL_Y, CRAFTING_TITLE_HEIGHT,
    )
    discovered = _every_item_id()  # a full grid to actually exercise scrolling
    max_scroll = crafting_max_scroll(discovered)
    assert max_scroll >= 0

    if max_scroll > 0:
        # Scrolling all the way down must bring the *last* cell into view
        # (that's the point of scrolling), and clicking it there must
        # resolve to that recipe.
        scrolled = list(_crafting_layout(max_scroll, discovered))
        last_recipe, last_rect = scrolled[-1]
        viewport_bottom = CRAFTING_PANEL_Y + crafting_panel_height(discovered)
        assert last_rect.bottom <= viewport_bottom + 1  # now fully on-screen

        hit = recipe_at_screen_pos(last_rect.center, max_scroll, discovered)
        assert hit is last_recipe

        # The first cell, after scrolling past it, sits above the visible
        # viewport -- clicking that (now off-screen) position must not
        # resolve to a recipe, since a real click there wouldn't land on
        # anything visible.
        _, first_rect_scrolled = scrolled[0]
        assert first_rect_scrolled.bottom < CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT
        assert recipe_at_screen_pos(first_rect_scrolled.center, max_scroll, discovered) is None

    # A click in the header bar (above the scrollable content) never hits a recipe.
    header_pos = (CRAFTING_PANEL_X + 20, CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT // 2)
    assert recipe_at_screen_pos(header_pos, 0, discovered) is None


def test_locked_recipe_never_appears_or_hit_tests_in_the_grid():
    from game.rendering.renderer import _crafting_layout

    recipe = recipe_registry.get("stone_pickaxe")  # needs wood + stone_block
    partially_discovered = {"wood"}  # missing stone_block -- still locked

    ids_in_grid = {r.id for r, _ in _crafting_layout(0, partially_discovered)}
    assert recipe.id not in ids_in_grid
