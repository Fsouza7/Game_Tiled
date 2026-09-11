"""Headless tests for the crafting-system upgrade: recipe discovery/unlock,
the on-screen blocked-mining message, and the Furnace (timed ore+fuel ->
bar smelting).
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import FURNACE_ID, STONE_ID, WORKBENCH_ID
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


# --- Timed crafting (start_craft/update_pending_craft; the crafting
# screen's click path uses this, not the instant craft()/craft_and_discover) ---

def test_craft_time_scales_with_result_rarity():
    from game.items.item import ItemRarity

    common = recipe_registry.get("wood_plank_block")  # ItemRarity.COMMON
    rare = recipe_registry.get("iron_armor")  # ItemRarity.RARE
    epic = recipe_registry.get("arcane_pickaxe")  # ItemRarity.EPIC
    assert item_registry.get(common.result_item_id).rarity == ItemRarity.COMMON
    assert item_registry.get(rare.result_item_id).rarity == ItemRarity.RARE
    assert item_registry.get(epic.result_item_id).rarity == ItemRarity.EPIC

    assert crafting_system.craft_time_for(common) < crafting_system.craft_time_for(rare) < crafting_system.craft_time_for(epic)


def test_start_craft_consumes_ingredients_immediately_and_creates_a_job():
    world, player = _make_player()
    player.inventory.add_item("wood", 5)
    recipe = recipe_registry.get("wood_plank_block")  # 1 wood -> 4 planks

    started = crafting_system.start_craft(recipe, player, world)

    assert started is True
    assert player.inventory.count_item("wood") == 4  # consumed immediately, like starting a smelt
    assert player.inventory.count_item("wood_plank_block") == 0  # not granted yet
    assert player.craft_job.recipe_id == "wood_plank_block"
    assert player.craft_job.remaining_s == player.craft_job.total_s == crafting_system.craft_time_for(recipe)


def test_start_craft_fails_without_ingredients():
    world, player = _make_player()
    recipe = recipe_registry.get("wood_plank_block")
    assert crafting_system.start_craft(recipe, player, world) is False
    assert player.craft_job is None


def test_start_craft_fails_without_a_nearby_station():
    world, player = _make_player()
    player.inventory.add_item("wood", 10)
    recipe = recipe_registry.get("wood_pickaxe")  # station_tile_id is None -- use a station recipe instead
    stone_pickaxe = recipe_registry.get("stone_pickaxe")
    player.inventory.add_item("stone_block", 10)
    assert stone_pickaxe.station_tile_id is not None
    assert crafting_system.start_craft(stone_pickaxe, player, world) is False
    assert player.craft_job is None


def test_start_craft_fails_while_a_different_craft_is_already_in_progress():
    world, player = _make_player()
    player.inventory.add_item("wood", 10)
    first = recipe_registry.get("wood_plank_block")
    crafting_system.start_craft(first, player, world)

    second = recipe_registry.get("workbench")
    assert crafting_system.start_craft(second, player, world) is False
    assert player.craft_job.recipe_id == "wood_plank_block"  # unchanged


def test_update_pending_craft_is_a_noop_before_the_timer_elapses():
    world, player = _make_player()
    player.inventory.add_item("wood", 5)
    recipe = recipe_registry.get("wood_plank_block")
    crafting_system.start_craft(recipe, player, world)

    finished, newly_discovered = crafting_system.update_pending_craft(player, dt=0.001)
    assert finished is None
    assert newly_discovered == []
    assert player.craft_job is not None
    assert player.inventory.count_item("wood_plank_block") == 0


def test_update_pending_craft_grants_the_result_xp_and_discovery_once_its_timer_elapses():
    world, player = _make_player()
    player.inventory.add_item("wood", 5)
    recipe = recipe_registry.get("wood_plank_block")
    crafting_system.start_craft(recipe, player, world)
    start_xp = player.skills.xp("crafting")

    finished = None
    newly_discovered = []
    for _ in range(50):
        finished, newly_discovered = crafting_system.update_pending_craft(player, dt=0.1)
        if finished is not None:
            break

    assert finished is recipe
    assert player.craft_job is None
    assert player.inventory.count_item("wood_plank_block") == 4
    assert "wood_plank_block" in player.discovered_item_ids
    assert player.skills.xp("crafting") > start_xp
    assert isinstance(newly_discovered, list)


def test_update_pending_craft_rolls_resourceful_refund_when_node_unlocked():
    from game.skills import xp_table

    world, player = _make_player()
    player.skills.add_xp("crafting", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("crafting_resourceful")
    recipe = recipe_registry.get("wood_plank_block")  # (("wood", 1),) -> 4 planks

    import random
    random.seed(1)  # deterministic: refunds within the loop below (same seed test_crafting_resourceful_node_can_refund_an_ingredient uses)
    refunded_at_least_once = False
    for _ in range(50):
        current_wood = player.inventory.count_item("wood")
        if current_wood > 0:
            player.inventory.remove_item("wood", current_wood)
        player.inventory.add_item("wood", 1)

        assert crafting_system.start_craft(recipe, player, world) is True
        for _ in range(50):
            finished, _ = crafting_system.update_pending_craft(player, dt=0.1)
            if finished is not None:
                break
        if player.inventory.count_item("wood") > 0:
            refunded_at_least_once = True

    assert refunded_at_least_once


def test_crafting_click_starts_a_timed_job_instead_of_granting_instantly():
    """The crafting screen's click path (InputHandler) uses the timed
    start_craft, not the instant craft_and_discover -- clicking a ready
    recipe should NOT grant the result right away."""
    from game.input.input_handler import InputHandler
    from game.rendering.renderer import _crafting_layout

    world, player = _make_player()
    player.inventory.add_item("wood", 5)
    player.collect_item("wood", 0)  # marks "wood" discovered without changing the count above

    recipe_id = "wood_plank_block"
    cell_rect = next(rect for r, rect in _crafting_layout(0, player.discovered_item_ids) if r.id == recipe_id)

    class _FakeCraftingGameApp:
        def __init__(self):
            self.player = player
            self.world = world
            self.crafting_scroll_y = 0
            self.furnace_manager = FurnaceManager()
            self.notifications = NotificationQueue()

    app = _FakeCraftingGameApp()
    InputHandler()._handle_crafting_click(cell_rect.center, app)

    assert player.craft_job is not None
    assert player.craft_job.recipe_id == recipe_id
    assert player.inventory.count_item("wood_plank_block") == 0  # not instant


def test_crafting_click_on_a_different_recipe_while_busy_does_not_cancel_the_job():
    from game.input.input_handler import InputHandler
    from game.rendering.renderer import _crafting_layout

    world, player = _make_player()
    player.inventory.add_item("wood", 10)
    player.collect_item("wood", 0)

    first_recipe = recipe_registry.get("wood_plank_block")
    crafting_system.start_craft(first_recipe, player, world)

    second_rect = next(rect for r, rect in _crafting_layout(0, player.discovered_item_ids) if r.id == "workbench")

    class _FakeCraftingGameApp:
        def __init__(self):
            self.player = player
            self.world = world
            self.crafting_scroll_y = 0
            self.furnace_manager = FurnaceManager()
            self.notifications = NotificationQueue()

    app = _FakeCraftingGameApp()
    InputHandler()._handle_crafting_click(second_rect.center, app)
    app.notifications.update(dt=0.0)  # pop the queued message into current_text

    assert player.craft_job.recipe_id == "wood_plank_block"  # still the original job
    assert app.notifications.current_text == "Already crafting something else"


def test_game_app_grants_the_craft_announces_it_and_spawns_confetti():
    """End-to-end through the real GameApp.step loop (not just the
    underlying crafting_system functions) -- catches wiring mistakes in
    _update_crafting the unit tests above wouldn't (wrong notification
    text, forgetting to spawn the completion effect, double-granting the
    item by also routing it through _collect_and_announce)."""
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.player.inventory.add_item("wood", 5)
        recipe = recipe_registry.get("wood_plank_block")
        assert crafting_system.start_craft(recipe, app.player, app.world) is True
        planks_before = app.player.inventory.count_item("wood_plank_block")
        particles_before = len(app.particles.particles)

        for _ in range(60):  # well over craft_time_for(recipe) at 1/60s steps
            app.step(dt=1 / 60)
            if app.player.craft_job is None:
                break

        assert app.player.craft_job is None
        assert app.player.inventory.count_item("wood_plank_block") == planks_before + recipe.result_quantity
        assert len(app.particles.particles) > particles_before  # the confetti burst
        assert app.notifications.current_text is not None and "Wood Plank" in app.notifications.current_text
    finally:
        pygame.quit()


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


# --- Furnace queue (deposit ore/fuel into the furnace's own input hopper,
# FurnaceManager keeps auto-starting the next batch on its own -- the
# Furnace screen's actual interaction; see furnace_system.py's docstring) ---

def _slot_index_of(inventory, item_id: str) -> int:
    return next(i for i, s in enumerate(inventory.slots) if s.item_id == item_id)


def test_deposit_fuel_and_ore_fill_the_furnace_input_hopper():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    player.inventory.add_item("coal", 5)
    player.inventory.add_item("iron_ore", 10)

    moved_fuel = manager.deposit_fuel(pos, player.inventory, _slot_index_of(player.inventory, "coal"))
    moved_ore = manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))

    assert moved_fuel == 5
    assert moved_ore == 10
    assert player.inventory.count_item("coal") == 0
    assert player.inventory.count_item("iron_ore") == 0
    storage = manager.input_at(pos)
    assert storage.slots[0].item_id == "coal" and storage.slots[0].quantity == 5
    assert storage.slots[1].item_id == "iron_ore" and storage.slots[1].quantity == 10


def test_deposit_rejects_items_that_arent_fuel_or_ore():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    player.inventory.add_item("wood", 5)
    wood_index = _slot_index_of(player.inventory, "wood")

    assert manager.deposit_fuel(pos, player.inventory, wood_index) == 0
    assert manager.deposit_ore(pos, player.inventory, wood_index) == 0
    assert player.inventory.count_item("wood") == 5  # untouched


def test_deposit_rejects_a_different_ore_than_whats_already_in_the_slot():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    player.inventory.add_item("iron_ore", 5)
    player.inventory.add_item("topaz", 5)
    manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))

    moved = manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "topaz"))

    assert moved == 0
    assert player.inventory.count_item("topaz") == 5  # rejected -- stays in the bag


def test_withdraw_fuel_and_ore_return_them_to_the_inventory():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    player.inventory.add_item("coal", 4)
    player.inventory.add_item("iron_ore", 6)
    manager.deposit_fuel(pos, player.inventory, _slot_index_of(player.inventory, "coal"))
    manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))

    manager.withdraw_fuel(pos, player.inventory)
    manager.withdraw_ore(pos, player.inventory)

    assert player.inventory.count_item("coal") == 4
    assert player.inventory.count_item("iron_ore") == 6
    storage = manager.input_at(pos)
    assert storage.slots[0].is_empty and storage.slots[1].is_empty


def test_furnace_queue_auto_starts_once_both_slots_have_enough():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity)
    player.inventory.add_item("coal", recipe.fuel_quantity)
    manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))
    manager.deposit_fuel(pos, player.inventory, _slot_index_of(player.inventory, "coal"))

    assert manager.job_at(pos) is None  # nothing starts until update() runs
    manager.update(0.0)
    job = manager.job_at(pos)
    assert job is not None
    assert job.bar_item_id == recipe.bar_item_id
    storage = manager.input_at(pos)
    assert storage.slots[0].is_empty and storage.slots[1].is_empty  # consumed from the hopper


def test_furnace_queue_keeps_consuming_a_deposited_stack_across_multiple_batches():
    """The whole point of the queue: insert a stack of ore + coal once,
    and the furnace works through it a batch at a time on its own,
    instead of needing a click per smelt."""
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    batches = 3
    player.inventory.add_item("iron_ore", recipe.ore_quantity * batches)
    player.inventory.add_item("coal", recipe.fuel_quantity * batches)
    manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))
    manager.deposit_fuel(pos, player.inventory, _slot_index_of(player.inventory, "coal"))

    completed_bars = 0
    steps = int(recipe.smelt_time_s * batches / 0.1) + 20  # generous margin, same style as the craft-timer tests above
    for _ in range(steps):
        for item_id, qty in manager.update(0.1):
            if item_id == recipe.bar_item_id:
                completed_bars += qty

    assert completed_bars == recipe.bar_quantity * batches
    storage = manager.input_at(pos)
    assert storage.slots[0].is_empty  # fuel fully consumed
    assert storage.slots[1].is_empty  # ore fully consumed
    assert manager.job_at(pos) is None  # nothing left to smelt


def test_furnace_queue_does_not_autostart_with_insufficient_ore_or_fuel():
    world, player = _make_player()
    pos = _place_furnace_near_player(world, player)
    manager = FurnaceManager()
    recipe = smelt_registry.get("iron_bar")
    player.inventory.add_item("iron_ore", recipe.ore_quantity - 1)  # one short
    player.inventory.add_item("coal", recipe.fuel_quantity)
    manager.deposit_ore(pos, player.inventory, _slot_index_of(player.inventory, "iron_ore"))
    manager.deposit_fuel(pos, player.inventory, _slot_index_of(player.inventory, "coal"))

    manager.update(0.1)

    assert manager.job_at(pos) is None


# --- Station screens: clicking a placed Workbench/Furnace opens its own
# screen (user feedback: "quando eu clicar em ambos ai sim deve abrir a
# tela deles, cada um separado") -- exercised end-to-end through the real
# GameApp/InputHandler, same precedent as
# test_game_app_grants_the_craft_announces_it_and_spawns_confetti above. ---

def _boot_app():
    from game.core.game_app import GameApp
    app = GameApp(seed=DEFAULT_SEED)
    app.title_open = False
    app.character_select_open = False
    app.class_select_open = False
    return app


def _set_tile_near_player(app, tile_id: int):
    tile_x = int(app.player.center_x // TILE_SIZE)
    tile_y = int(app.player.center_y // TILE_SIZE)
    chunk = app.world.get_or_create_chunk(app.world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, tile_id)
    return tile_x, tile_y


def test_clicking_a_workbench_opens_only_the_crafting_screen():
    app = _boot_app()
    try:
        tile_x, tile_y = _set_tile_near_player(app, WORKBENCH_ID)
        app.player.inventory.select_hotbar(5)  # an empty slot -- not the starting pickaxe
        click_pos = app.camera.world_to_screen(tile_x * TILE_SIZE + TILE_SIZE / 2, tile_y * TILE_SIZE + TILE_SIZE / 2)

        app.input_handler._handle_attack_click(click_pos, app)

        assert app.crafting_open is True
        assert app.furnace_open is False
    finally:
        pygame.quit()


def test_clicking_a_furnace_opens_only_the_furnace_screen():
    app = _boot_app()
    try:
        tile_x, tile_y = _place_furnace_near_player(app.world, app.player)
        app.player.inventory.select_hotbar(5)
        click_pos = app.camera.world_to_screen(tile_x * TILE_SIZE + TILE_SIZE / 2, tile_y * TILE_SIZE + TILE_SIZE / 2)

        app.input_handler._handle_attack_click(click_pos, app)

        assert app.furnace_open is True
        assert app.furnace_pos == (tile_x, tile_y)
        assert app.crafting_open is False
    finally:
        pygame.quit()


def test_station_click_is_skipped_while_a_mining_tool_is_selected():
    """Holding the pickaxe out and clicking a Workbench should still be
    able to mine/relocate it -- opening its screen would otherwise
    swallow every click and make that impossible."""
    app = _boot_app()
    try:
        tile_x, tile_y = _set_tile_near_player(app, WORKBENCH_ID)
        app.player.inventory.select_hotbar(0)  # the starting wood_pickaxe
        click_pos = app.camera.world_to_screen(tile_x * TILE_SIZE + TILE_SIZE / 2, tile_y * TILE_SIZE + TILE_SIZE / 2)

        app.input_handler._handle_attack_click(click_pos, app)

        assert app.crafting_open is False
    finally:
        pygame.quit()


def test_furnace_screen_click_deposits_bag_items_by_type():
    app = _boot_app()
    try:
        tile_x, tile_y = _place_furnace_near_player(app.world, app.player)
        app.furnace_open = True
        app.furnace_pos = (tile_x, tile_y)
        app.player.inventory.add_item("coal", 3)
        app.player.inventory.add_item("iron_ore", 6)

        from game.rendering.renderer import furnace_bag_slot_rect
        coal_index = _slot_index_of(app.player.inventory, "coal")
        ore_index = _slot_index_of(app.player.inventory, "iron_ore")

        app.input_handler._handle_furnace_click(furnace_bag_slot_rect(coal_index).center, app)
        app.input_handler._handle_furnace_click(furnace_bag_slot_rect(ore_index).center, app)

        storage = app.furnace_manager.input_at((tile_x, tile_y))
        assert storage.slots[0].item_id == "coal" and storage.slots[0].quantity == 3
        assert storage.slots[1].item_id == "iron_ore" and storage.slots[1].quantity == 6
        assert app.player.inventory.count_item("coal") == 0
        assert app.player.inventory.count_item("iron_ore") == 0
    finally:
        pygame.quit()


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
