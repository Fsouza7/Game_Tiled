"""Headless tests for the craftable Personal Chest: shared player-bound
stash, click-to-transfer, T-to-open while in range, and save/load.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH, PERSONAL_CHEST_SLOTS,
)
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import PERSONAL_CHEST_ID
from game.items import item_registry
from game.crafting import recipe_registry
from game.inventory.inventory import Inventory, transfer_stack
from game.crafting.furnace_system import nearest_station_tile
from game.core import save_system
from game.core.world_clock import WorldClock
from game.crafting.furnace_system import FurnaceManager
from game.input.input_handler import InputHandler
from game.rendering.renderer import (
    chest_bag_slot_rect, chest_storage_slot_rect,
    chest_bag_index_at_screen_pos, chest_storage_index_at_screen_pos,
)
from game.core.notifications import NotificationQueue
from game.npcs.npc import Npc
from game.npcs import npc_registry


def _make_world_and_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _place_personal_chest_near_player(world, player):
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, PERSONAL_CHEST_ID)
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
        self.notifications = NotificationQueue()

    def close_npc_panel(self):
        self.talking_to = None
        self.npc_shop_open = False

    def close_chest(self):
        self.chest_open = False


# --- registry ---

def test_personal_chest_item_recipe_and_tile_are_registered():
    item = item_registry.get("personal_chest")
    assert item.places_tile_id == PERSONAL_CHEST_ID
    recipe = recipe_registry.get("personal_chest")
    assert recipe.result_item_id == "personal_chest"
    assert recipe.station_tile_id is None
    assert recipe.ingredients == (("wood", 8),)


def test_personal_chest_starts_empty_with_configured_size():
    _, player = _make_world_and_player()
    assert len(player.personal_chest.slots) == PERSONAL_CHEST_SLOTS
    assert all(s.is_empty for s in player.personal_chest.slots)


# --- transfer ---

def test_transfer_stack_moves_the_whole_stack_when_dest_has_room():
    source = Inventory(4)
    dest = Inventory(4)
    source.add_item("wood", 12)
    moved = transfer_stack(source, 0, dest)
    assert moved == 12
    assert source.count_item("wood") == 0
    assert dest.count_item("wood") == 12


def test_transfer_stack_keeps_leftover_when_dest_is_full():
    source = Inventory(2)
    dest = Inventory(1)
    source.add_item("dirt_block", 10)
    dest.add_item("stone_block", 99)
    moved = transfer_stack(source, 0, dest)
    assert moved == 0
    assert source.count_item("dirt_block") == 10
    assert dest.count_item("dirt_block") == 0


def test_transfer_stack_partially_fills_an_existing_dest_stack():
    source = Inventory(2)
    dest = Inventory(1)
    source.add_item("wood", 10)
    dest.add_item("wood", 95)
    moved = transfer_stack(source, 0, dest)
    assert moved == 4
    assert source.count_item("wood") == 6
    assert dest.count_item("wood") == 99


# --- proximity ---

def test_nearest_station_finds_a_placed_personal_chest():
    world, player = _make_world_and_player()
    pos = _place_personal_chest_near_player(world, player)
    found = nearest_station_tile(world, player.center_x, player.center_y, PERSONAL_CHEST_ID)
    assert found == pos


def test_t_opens_personal_chest_when_in_range():
    world, player = _make_world_and_player()
    _place_personal_chest_near_player(world, player)
    app = _FakeChestGameApp(player, world)
    InputHandler()._handle_talk(app)
    assert app.chest_open is True


def test_t_does_not_open_chest_when_none_is_nearby():
    world, player = _make_world_and_player()
    app = _FakeChestGameApp(player, world)
    InputHandler()._handle_talk(app)
    assert app.chest_open is False


def test_t_prefers_npc_over_chest():
    world, player = _make_world_and_player()
    _place_personal_chest_near_player(world, player)
    npc = Npc(npc_registry.get("guide"), player.x, player.y)
    app = _FakeChestGameApp(player, world, npcs=[npc])
    InputHandler()._handle_talk(app)
    assert app.talking_to is npc
    assert app.chest_open is False


def test_t_toggles_chest_closed():
    world, player = _make_world_and_player()
    _place_personal_chest_near_player(world, player)
    app = _FakeChestGameApp(player, world)
    handler = InputHandler()
    handler._handle_talk(app)
    assert app.chest_open is True
    handler._handle_talk(app)
    assert app.chest_open is False


def test_click_moves_bag_stack_into_the_stash():
    world, player = _make_world_and_player()
    player.inventory.add_item("wood", 8)
    wood_index = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "wood")
    app = _FakeChestGameApp(player, world)
    app.chest_open = True
    pos = chest_bag_slot_rect(wood_index).center
    assert chest_bag_index_at_screen_pos(pos, len(player.inventory.slots)) == wood_index
    InputHandler()._handle_chest_click(pos, app)
    assert player.inventory.count_item("wood") == 0
    assert player.personal_chest.count_item("wood") == 8


def test_click_moves_stash_stack_back_to_the_bag():
    world, player = _make_world_and_player()
    player.personal_chest.add_item("coal", 5)
    app = _FakeChestGameApp(player, world)
    app.chest_open = True
    pos = chest_storage_slot_rect(0).center
    assert chest_storage_index_at_screen_pos(pos, len(player.personal_chest.slots)) == 0
    InputHandler()._handle_chest_click(pos, app)
    assert player.personal_chest.count_item("coal") == 0
    assert player.inventory.count_item("coal") == 5


# --- save ---

def test_personal_chest_round_trips_through_save():
    world, player = _make_world_and_player()
    player.personal_chest.add_item("iron_bar", 3)
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    _, player2, _, _ = save_system.deserialize(data)
    assert player2.personal_chest.count_item("iron_bar") == 3


def test_old_save_without_personal_chest_stays_empty():
    world, player = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    del data["player"]["personal_chest"]
    _, player2, _, _ = save_system.deserialize(data)
    assert all(s.is_empty for s in player2.personal_chest.slots)


def test_game_app_draws_the_open_chest_panel():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        _place_personal_chest_near_player(app.world, app.player)
        app.chest_open = True
        app.player.inventory.add_item("wood", 4)
        app.step(dt=1 / 60)
    finally:
        pygame.quit()
