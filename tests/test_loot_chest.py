"""Headless tests for world-generated loot Chests (found in structures --
Houses, Ruins, Underground Rooms): opened the same way as the Personal
Chest (T while in range) but each one gets its own one-time random loot
roll instead of a shared player-bound stash. See game/world/loot_chest.py.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH,
    LOOT_CHEST_SLOTS, LOOT_CHEST_MIN_ROLLS, LOOT_CHEST_MAX_ROLLS,
    STATION_SEARCH_RADIUS_TILES,
)
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import PERSONAL_CHEST_ID, CHEST_ID
from game.world import loot_chest
from game.core import save_system
from game.core.world_clock import WorldClock
from game.crafting.furnace_system import FurnaceManager
from game.input.input_handler import InputHandler
from game.rendering.renderer import chest_bag_slot_rect, chest_storage_slot_rect
from game.core.notifications import NotificationQueue


def _make_world_and_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _place_tile_near_player(world, player, tile_id):
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, tile_id)
    return tile_x, tile_y


class _FakeChestGameApp:
    def __init__(self, player, world, npcs=None):
        self.player = player
        self.world = world
        self.npcs = npcs or []
        self.paused = False
        self.inventory_open = False
        self.crafting_open = False
        self.skills_open = False
        self.talking_to = None
        self.npc_shop_open = False
        self.chest_open = False
        self.open_chest_pos = None
        self.notifications = NotificationQueue()

    def close_npc_panel(self):
        self.talking_to = None
        self.npc_shop_open = False

    def close_chest(self):
        self.chest_open = False
        self.open_chest_pos = None


# --- deterministic roll ---

def test_roll_is_deterministic_for_the_same_seed_and_position():
    a = loot_chest.roll_chest_loot(DEFAULT_SEED, 500, 40)
    b = loot_chest.roll_chest_loot(DEFAULT_SEED, 500, 40)
    a_contents = [(s.item_id, s.quantity) for s in a.slots]
    b_contents = [(s.item_id, s.quantity) for s in b.slots]
    assert a_contents == b_contents


def test_roll_varies_by_position():
    rolls = [loot_chest.roll_chest_loot(DEFAULT_SEED, x, 40) for x in range(500, 520)]
    signatures = {tuple(sorted((s.item_id, s.quantity) for s in r.slots if not s.is_empty)) for r in rolls}
    assert len(signatures) > 1, "every position rolled identical loot -- position isn't mixed into the seed"


def test_roll_contains_distinct_items_from_the_known_pool_within_bounds():
    inventory = loot_chest.roll_chest_loot(DEFAULT_SEED, 777, 12)
    pool_ids = {item_id for item_id, _, _, _ in loot_chest.LOOT_POOL}
    filled = [s for s in inventory.slots if not s.is_empty]
    assert LOOT_CHEST_MIN_ROLLS <= len(filled) <= LOOT_CHEST_MAX_ROLLS
    ids = [s.item_id for s in filled]
    assert len(ids) == len(set(ids)), "a rolled chest should never roll the same item twice"
    assert all(item_id in pool_ids for item_id in ids)
    assert len(inventory.slots) == LOOT_CHEST_SLOTS


# --- World caching ---

def test_get_chest_inventory_returns_the_same_instance_on_repeat_calls():
    world, _ = _make_world_and_player()
    first = world.get_chest_inventory(10, 20)
    second = world.get_chest_inventory(10, 20)
    assert first is second


def test_taking_an_item_out_of_a_loot_chest_persists_on_the_cached_instance():
    world, _ = _make_world_and_player()
    inventory = world.get_chest_inventory(10, 20)
    filled_index = next(i for i, s in enumerate(inventory.slots) if not s.is_empty)
    item_id = inventory.slots[filled_index].item_id
    inventory.remove_item(item_id, inventory.slots[filled_index].quantity)
    assert world.get_chest_inventory(10, 20).count_item(item_id) == 0


def test_untouched_chest_is_not_cached_until_first_opened():
    world, _ = _make_world_and_player()
    assert world.chest_loot == {}
    world.get_chest_inventory(10, 20)
    assert (10, 20) in world.chest_loot


# --- T-to-open ---

def test_t_opens_a_world_loot_chest_when_in_range():
    world, player = _make_world_and_player()
    pos = _place_tile_near_player(world, player, CHEST_ID)
    app = _FakeChestGameApp(player, world)
    InputHandler()._handle_talk(app)
    assert app.chest_open is True
    assert app.open_chest_pos == pos


def test_personal_chest_takes_priority_over_a_loot_chest_when_both_in_range():
    world, player = _make_world_and_player()
    _place_tile_near_player(world, player, PERSONAL_CHEST_ID)
    app = _FakeChestGameApp(player, world)
    InputHandler()._handle_talk(app)
    assert app.chest_open is True
    assert app.open_chest_pos is None  # None == the player's own Personal Chest


def test_t_toggles_loot_chest_closed_and_clears_open_chest_pos():
    world, player = _make_world_and_player()
    _place_tile_near_player(world, player, CHEST_ID)
    app = _FakeChestGameApp(player, world)
    handler = InputHandler()
    handler._handle_talk(app)
    assert app.chest_open is True
    handler._handle_talk(app)
    assert app.chest_open is False
    assert app.open_chest_pos is None


# --- click-to-transfer ---

def test_click_moves_loot_into_the_bag():
    world, player = _make_world_and_player()
    pos = _place_tile_near_player(world, player, CHEST_ID)
    loot = world.get_chest_inventory(*pos)
    loot.slots[0].item_id = "iron_bar"
    loot.slots[0].quantity = 3

    app = _FakeChestGameApp(player, world)
    app.chest_open = True
    app.open_chest_pos = pos
    click_pos = chest_storage_slot_rect(0).center
    InputHandler()._handle_chest_click(click_pos, app)

    assert player.inventory.count_item("iron_bar") == 3
    assert loot.count_item("iron_bar") == 0


def test_click_moves_bag_item_into_the_loot_chest():
    world, player = _make_world_and_player()
    pos = _place_tile_near_player(world, player, CHEST_ID)
    player.inventory.add_item("wood", 5)
    wood_index = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "wood")

    app = _FakeChestGameApp(player, world)
    app.chest_open = True
    app.open_chest_pos = pos
    click_pos = chest_bag_slot_rect(wood_index).center
    InputHandler()._handle_chest_click(click_pos, app)

    assert player.inventory.count_item("wood") == 0
    assert world.get_chest_inventory(*pos).count_item("wood") == 5


def test_loot_chests_at_different_positions_are_independent():
    world, player = _make_world_and_player()
    a = world.get_chest_inventory(10, 20)
    b = world.get_chest_inventory(50, 20)
    assert a is not b
    a.slots[0].item_id = "coin"
    a.slots[0].quantity = 99
    assert world.get_chest_inventory(50, 20) is b
    assert (b.slots[0].item_id, b.slots[0].quantity) != ("coin", 99)


# --- proximity close ---

def test_close_chest_if_out_of_range_closes_a_distant_loot_chest():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        pos = _place_tile_near_player(app.world, app.player, CHEST_ID)
        app.chest_open = True
        app.open_chest_pos = pos

        app._close_chest_if_out_of_range()
        assert app.chest_open is True  # still standing right next to it

        app.player.x += (STATION_SEARCH_RADIUS_TILES + 5) * TILE_SIZE
        app._close_chest_if_out_of_range()
        assert app.chest_open is False
        assert app.open_chest_pos is None
    finally:
        pygame.quit()


def test_active_chest_inventory_resolves_personal_vs_loot():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.open_chest_pos = None
        assert app.active_chest_inventory() is app.player.personal_chest

        pos = (10, 20)
        app.open_chest_pos = pos
        assert app.active_chest_inventory() is app.world.get_chest_inventory(*pos)
    finally:
        pygame.quit()


# --- save/load ---

def test_touched_loot_chest_round_trips_through_save():
    world, player = _make_world_and_player()
    inventory = world.get_chest_inventory(10, 20)
    inventory.slots[0].item_id = "iron_bar"
    inventory.slots[0].quantity = 2
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    world2, _, _, _ = save_system.deserialize(data)

    assert world2.get_chest_inventory(10, 20).count_item("iron_bar") == 2


def test_untouched_loot_chest_is_not_saved():
    world, player = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    assert data["chest_loot"] == []


def test_old_save_without_chest_loot_field_loads_with_empty_chest_cache():
    world, player = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    del data["chest_loot"]
    world2, _, _, _ = save_system.deserialize(data)
    assert world2.chest_loot == {}


# --- rendering ---

def test_draw_chest_panel_does_not_crash_for_personal_or_loot_storage():
    import pygame as pg
    from game.rendering.renderer import Renderer
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    pg.init()
    pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pg.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    _, player = _make_world_and_player()

    renderer._draw_chest_panel(window, player, player.personal_chest)

    world, _ = _make_world_and_player()
    loot = world.get_chest_inventory(10, 20)
    renderer._draw_chest_panel(window, player, loot)
