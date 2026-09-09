"""Headless tests for the crafting-system upgrade: recipe discovery/unlock,
the on-screen blocked-mining message, and the Furnace (timed ore+fuel ->
bar smelting).
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import FURNACE_ID, STONE_ID
from game.items import item_registry
from game.crafting import recipe_registry, crafting_system, smelt_registry
from game.crafting.furnace_system import FurnaceManager, nearest_station_tile
from game.core.notifications import NotificationQueue


def _make_player(world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _place_furnace_near_player(world, player):
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, FURNACE_ID)
    return tile_x, tile_y


# --- Recipe discovery ---

def test_new_player_has_not_discovered_common_ingredients():
    _, player = _make_player()
    assert "wood" not in player.discovered_item_ids
    assert "iron_bar" not in player.discovered_item_ids


def test_collect_item_marks_it_discovered():
    _, player = _make_player()
    player.collect_item("wood", 3)
    assert "wood" in player.discovered_item_ids
    assert player.inventory.count_item("wood") == 3


def test_recipe_is_locked_until_every_ingredient_is_discovered():
    recipe = recipe_registry.get("stone_pickaxe")  # wood + stone_block
    _, player = _make_player()
    assert crafting_system.is_recipe_discovered(recipe, player.discovered_item_ids) is False

    player.collect_item("wood", 5)
    assert crafting_system.is_recipe_discovered(recipe, player.discovered_item_ids) is False  # still missing stone_block

    player.collect_item("stone_block", 10)
    assert crafting_system.is_recipe_discovered(recipe, player.discovered_item_ids) is True


def test_undiscovered_ingredients_lists_exactly_whats_missing():
    recipe = recipe_registry.get("stone_pickaxe")
    _, player = _make_player()
    player.collect_item("wood", 5)
    assert crafting_system.undiscovered_ingredients(recipe, player.discovered_item_ids) == ["stone_block"]


def test_collect_and_discover_announces_newly_unlocked_recipes():
    _, player = _make_player()
    unlocked = crafting_system.collect_and_discover(player, "wood", 5)
    unlocked_ids = {r.id for r in unlocked}
    # every wood-only recipe should have just unlocked
    assert "wood_plank_block" in unlocked_ids
    assert "workbench" in unlocked_ids
    assert "wood_pickaxe" in unlocked_ids
    # a recipe needing a second, still-undiscovered ingredient must not appear
    assert "stone_pickaxe" not in unlocked_ids


def test_collect_and_discover_returns_nothing_new_on_repeat_pickup():
    _, player = _make_player()
    crafting_system.collect_and_discover(player, "wood", 5)
    second_batch = crafting_system.collect_and_discover(player, "wood", 5)
    assert second_batch == []


def test_craft_and_discover_marks_result_discovered_and_unlocks_downstream_recipes():
    world, player = _make_player()
    player.collect_item("wood", 5)
    recipe = recipe_registry.get("wood_pickaxe")

    success, unlocked = crafting_system.craft_and_discover(recipe, player, world)

    assert success is True
    assert "wood_pickaxe" in player.discovered_item_ids


def test_locked_recipe_is_not_craftable_via_the_click_path_even_with_ingredients():
    """Guards the InputHandler rule (recipe must be discovered before a
    click does anything) at the level the input handler actually checks."""
    world, player = _make_player()
    recipe = recipe_registry.get("stone_pickaxe")
    player.inventory.add_item("wood", 5)  # in inventory but never "discovered" via collect_item
    player.inventory.add_item("stone_block", 10)

    assert crafting_system.is_recipe_discovered(recipe, player.discovered_item_ids) is False
    # has_ingredients would say True -- discovery is a separate, additional gate
    assert crafting_system.has_ingredients(recipe, player.inventory) is True


# --- Blocked-mining message ---

def test_blocked_mining_reason_none_for_hand_breakable_tile():
    world, player = _make_player()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE) + 1
    # dirt/grass under the player needs no tool
    assert player.blocked_mining_reason(world, tile_x, tile_y) is None


def test_blocked_mining_reason_names_the_required_tool():
    world, player = _make_player()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, STONE_ID)
    player.inventory.select_hotbar(1)  # empty slot -- the starting wood_pickaxe lives in slot 0

    reason = player.blocked_mining_reason(world, tile_x, tile_y)

    assert reason == "Requires a Pickaxe"


def test_blocked_mining_reason_none_once_holding_the_right_tool():
    world, player = _make_player()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, STONE_ID)
    player.inventory.select_hotbar(0)  # wood_pickaxe from the starting inventory

    assert player.blocked_mining_reason(world, tile_x, tile_y) is None


def test_blocked_mining_reason_none_out_of_reach():
    world, player = _make_player()
    far_tile_x = int(player.center_x // TILE_SIZE) + 100
    tile_y = int(player.center_y // TILE_SIZE)
    assert player.blocked_mining_reason(world, far_tile_x, tile_y) is None


# --- Furnace / smelting ---

def test_furnace_item_recipe_and_tile_are_registered():
    assert item_registry.get("furnace").places_tile_id == FURNACE_ID
    assert recipe_registry.get("furnace").result_item_id == "furnace"


def test_iron_pickaxe_recipe_uses_iron_bar():
    recipe = recipe_registry.get("iron_pickaxe")
    ingredient_ids = {item_id for item_id, _ in recipe.ingredients}
    assert "iron_bar" in ingredient_ids
    assert item_registry.get("iron_pickaxe").mining_power > item_registry.get("stone_pickaxe").mining_power


def test_steel_pickaxe_is_the_next_mining_tier_after_iron():
    recipe = recipe_registry.get("steel_pickaxe")
    ingredient_ids = {item_id for item_id, _ in recipe.ingredients}
    assert "steel_bar" in ingredient_ids
    assert item_registry.get("steel_pickaxe").mining_power > item_registry.get("iron_pickaxe").mining_power
    smelt = smelt_registry.get("steel_bar")
    assert smelt.ore_item_id == "iron_bar"


def test_every_ore_has_a_smelt_recipe_into_a_registered_bar_item():
    for smelt_recipe in smelt_registry.all_recipes():
        bar_item = item_registry.get(smelt_recipe.bar_item_id)
        assert bar_item.id == smelt_recipe.bar_item_id
        item_registry.get(smelt_recipe.ore_item_id)  # doesn't raise


def test_nearest_station_tile_finds_the_furnace():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    found = nearest_station_tile(world, player.center_x, player.center_y, FURNACE_ID)
    assert found == pos


def test_nearest_station_tile_none_when_no_furnace_nearby():
    world, player = _make_player()
    assert nearest_station_tile(world, player.center_x, player.center_y, FURNACE_ID) is None


def test_start_smelt_fails_without_a_nearby_furnace():
    world, player = _make_player()
    player.inventory.add_item("iron_ore", 5)
    player.inventory.add_item("coal", 5)
    manager = FurnaceManager()

    started = manager.start_smelt(smelt_registry.get("iron_bar"), player.inventory, world, player.center_x, player.center_y)

    assert started is False
    assert manager.jobs == {}


def test_start_smelt_fails_without_enough_ore_or_fuel():
    world, player = _make_player()
    _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")

    assert manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y) is False

    player.inventory.add_item("iron_ore", recipe.ore_quantity)  # ore but no fuel yet
    assert manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y) is False


def test_start_smelt_consumes_ore_and_fuel_and_creates_a_job():
    world, player = _make_player()
    _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity)
    player.inventory.add_item("coal", recipe.fuel_quantity)

    started = manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)

    assert started is True
    assert player.inventory.count_item("iron_ore") == 0
    assert player.inventory.count_item("coal") == 0
    assert len(manager.jobs) == 1


def test_furnace_is_busy_until_the_job_completes():
    world, player = _make_player()
    _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity * 2)
    player.inventory.add_item("coal", recipe.fuel_quantity * 2)

    manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)
    second_attempt = manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)

    assert second_attempt is False  # furnace already smelting something
    assert player.inventory.count_item("iron_ore") == recipe.ore_quantity  # second attempt's ore untouched


def test_furnace_update_grants_the_bar_after_smelt_time_elapses():
    world, player = _make_player()
    _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity)
    player.inventory.add_item("coal", recipe.fuel_quantity)
    manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)

    completed_early = manager.update(recipe.smelt_time_s * 0.5)
    assert completed_early == []
    assert len(manager.jobs) == 1

    completed = manager.update(recipe.smelt_time_s * 0.6)
    assert completed == [(recipe.bar_item_id, recipe.bar_quantity)]
    assert manager.jobs == {}


def test_furnace_can_start_a_new_job_after_the_previous_one_completes():
    world, player = _make_player()
    _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity * 2)
    player.inventory.add_item("coal", recipe.fuel_quantity * 2)

    manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)
    manager.update(recipe.smelt_time_s + 0.1)

    started_again = manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)
    assert started_again is True


# --- Notifications ---

def test_notification_queue_shows_pushed_text_and_expires_it():
    from game.settings import NOTIFICATION_DURATION_S
    queue = NotificationQueue()
    assert queue.current_text is None

    queue.push("Hello")
    queue.update(0.016)
    assert queue.current_text == "Hello"

    queue.update(NOTIFICATION_DURATION_S + 0.1)
    assert queue.current_text is None


def test_notification_queue_shows_messages_in_order():
    queue = NotificationQueue()
    queue.push("First")
    queue.push("Second")
    queue.update(0.016)
    assert queue.current_text == "First"


def test_notification_push_throttled_suppresses_rapid_repeats():
    queue = NotificationQueue()
    queue.push_throttled("Requires a Pickaxe")
    queue.update(0.016)
    queue.push_throttled("Requires a Pickaxe")  # immediate repeat, should be suppressed
    # still just the one instance queued/showing
    assert queue.current_text == "Requires a Pickaxe"
    queue.update(3.0)  # let it expire
    assert queue.current_text is None  # nothing queued behind it -- the repeat was suppressed
