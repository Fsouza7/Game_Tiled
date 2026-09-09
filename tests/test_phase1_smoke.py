"""Headless smoke tests for Phase 1: world gen, physics, mining, building,
inventory. No real display is required (see conftest.py).

Run with: python -m pytest tests/test_phase1_smoke.py -v
"""
import pygame  # noqa: F401  (import order matters: after conftest sets SDL_VIDEODRIVER)

from game.settings import (
    TILE_SIZE, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, DEFAULT_SEED,
    BEDROCK_ROWS, PLAYER_MAX_JUMPS, PLAYER_JUMP_VELOCITY, PLAYER_DOUBLE_JUMP_VELOCITY,
    PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S,
)
from game.world.world import World
from game.world import tile_registry
from game.world.tile_registry import AIR_ID, GRASS_ID, DIRT_ID, STONE_ID, BEDROCK_ID
from game.entities.player import Player
from game.inventory.inventory import Inventory
from game.core.camera import Camera


# --- world generation ---

def test_world_generation_is_deterministic():
    world_a = World(DEFAULT_SEED)
    world_b = World(DEFAULT_SEED)
    for x in (0, 5, 100, 500, WORLD_WIDTH_TILES - 1):
        for y in (0, 40, 45, 60, 100, WORLD_HEIGHT_TILES - 1):
            assert world_a.get_tile(x, y) == world_b.get_tile(x, y)


def test_world_layers_above_and_below_surface():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1

    assert world.get_tile(x, surface_y - 5) == AIR_ID
    assert world.get_tile(x, surface_y) == GRASS_ID
    assert world.get_tile(x, surface_y + 2) == DIRT_ID

    bottom_row = WORLD_HEIGHT_TILES - 1
    assert world.get_tile(x, bottom_row) == BEDROCK_ID


def test_world_out_of_bounds_is_treated_as_air_and_solid():
    world = World(DEFAULT_SEED)
    assert world.get_tile(-1, 0) == AIR_ID
    assert world.get_tile(WORLD_WIDTH_TILES + 10, 0) == AIR_ID
    assert world.is_solid(-1, 0) is True  # can't fall out of the world
    assert world.is_solid(WORLD_WIDTH_TILES + 10, 0) is True


def test_bedrock_cannot_be_broken():
    world = World(DEFAULT_SEED)
    x = 10
    bottom_row = WORLD_HEIGHT_TILES - 1
    assert world.get_tile(x, bottom_row) == BEDROCK_ID
    drop = world.try_break_tile(x, bottom_row)
    assert drop is None
    assert world.get_tile(x, bottom_row) == BEDROCK_ID


# --- mining ---

def _find_stone_below(world, x, start_y):
    for y in range(start_y, WORLD_HEIGHT_TILES - BEDROCK_ROWS):
        if world.get_tile(x, y) == STONE_ID:
            return y
    raise AssertionError("no stone tile found to test mining against")


def test_mining_dirt_by_hand_and_receives_item():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    dirt_y = surface_y + 2
    assert world.get_tile(x, dirt_y) == DIRT_ID

    player = Player(x * TILE_SIZE, dirt_y * TILE_SIZE)  # standing right at the target
    player.inventory.remove_item("wood_pickaxe", 1)  # bare hands only

    drop = None
    for _ in range(200):
        drop = player.try_mine(world, x, dirt_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "dirt_block"
    assert world.get_tile(x, dirt_y) == AIR_ID


def test_mining_stone_requires_pickaxe():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    stone_y = _find_stone_below(world, x, surface_y + 12)

    player = Player(x * TILE_SIZE, stone_y * TILE_SIZE)  # standing right at the target
    player.inventory.remove_item("wood_pickaxe", 1)  # no tool equipped

    for _ in range(50):
        drop = player.try_mine(world, x, stone_y, dt=0.1)
        assert drop is None
    assert world.get_tile(x, stone_y) == STONE_ID


def test_mining_stone_with_pickaxe_succeeds():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    stone_y = _find_stone_below(world, x, surface_y + 12)

    player = Player(x * TILE_SIZE, stone_y * TILE_SIZE)  # standing right at the target
    assert player.inventory.count_item("wood_pickaxe") == 1  # default loadout

    drop = None
    for _ in range(200):
        drop = player.try_mine(world, x, stone_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "stone_block"
    assert world.get_tile(x, stone_y) == AIR_ID


def test_mining_out_of_reach_does_nothing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    far_y = surface_y + 2

    player = Player(x * TILE_SIZE, (surface_y - 5) * TILE_SIZE)
    far_x = x + 50  # well beyond PLAYER_REACH_TILES
    drop = player.try_mine(world, far_x, far_y, dt=0.1)
    assert drop is None


# --- building ---

def test_place_block_next_to_solid_ground_succeeds():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    target_y = surface_y - 1  # directly above the grass block

    placed = world.try_place_tile(x, target_y, tile_registry.DIRT_ID)
    assert placed is True
    assert world.get_tile(x, target_y) == DIRT_ID


def test_place_block_floating_in_open_air_fails():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    floating_y = surface_y - 10  # far from any solid tile

    placed = world.try_place_tile(x, floating_y, tile_registry.DIRT_ID)
    assert placed is False
    assert world.get_tile(x, floating_y) == AIR_ID


def test_cannot_place_on_occupied_tile():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    placed = world.try_place_tile(x, surface_y, tile_registry.DIRT_ID)  # already grass
    assert placed is False


# --- inventory ---

def test_inventory_add_stacks_and_overflows_into_new_slot():
    inv = Inventory()
    from game.settings import DEFAULT_STACK_SIZE
    leftover = inv.add_item("dirt_block", DEFAULT_STACK_SIZE + 10)
    assert leftover == 0
    assert inv.count_item("dirt_block") == DEFAULT_STACK_SIZE + 10
    filled_slots = [s for s in inv.slots if s.item_id == "dirt_block"]
    assert len(filled_slots) == 2


def test_inventory_remove_partial_and_full():
    inv = Inventory()
    inv.add_item("coal", 5)
    removed = inv.remove_item("coal", 3)
    assert removed == 3
    assert inv.count_item("coal") == 2
    removed_more = inv.remove_item("coal", 10)
    assert removed_more == 2
    assert inv.count_item("coal") == 0


def test_hotbar_selection():
    inv = Inventory()
    inv.slots[3].item_id = "coal"
    inv.slots[3].quantity = 1
    inv.select_hotbar(3)
    selected = inv.get_selected_item()
    assert selected is not None
    assert selected.item_id == "coal"


def test_swap_slots_exchanges_contents():
    inv = Inventory()
    inv.slots[2].item_id = "coal"
    inv.slots[2].quantity = 5
    inv.slots[7].item_id = "wood"
    inv.slots[7].quantity = 2

    inv.swap_slots(2, 7)

    assert inv.slots[2].item_id == "wood" and inv.slots[2].quantity == 2
    assert inv.slots[7].item_id == "coal" and inv.slots[7].quantity == 5


def test_swap_slots_with_an_empty_slot_moves_the_item():
    inv = Inventory()
    inv.slots[0].item_id = "coal"
    inv.slots[0].quantity = 3

    inv.swap_slots(0, 5)

    assert inv.slots[0].is_empty
    assert inv.slots[5].item_id == "coal" and inv.slots[5].quantity == 3


def test_swap_slots_with_itself_is_a_no_op():
    inv = Inventory()
    inv.slots[1].item_id = "coal"
    inv.slots[1].quantity = 4

    inv.swap_slots(1, 1)

    assert inv.slots[1].item_id == "coal" and inv.slots[1].quantity == 4


# --- player physics ---

def test_player_gravity_lands_on_ground():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 20) * TILE_SIZE)

    for _ in range(300):
        player.physics_step(world, dt=1 / 60)
        if player.on_ground:
            break

    assert player.on_ground is True
    ground_top_px = surface_y * TILE_SIZE
    assert abs((player.y + player.height) - ground_top_px) < TILE_SIZE


def test_fall_damage_applied_on_hard_landing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    start_row = max(1, surface_y - 40)  # stay inside the world's top boundary
    player = Player(x * TILE_SIZE, start_row * TILE_SIZE)

    for _ in range(600):
        player.physics_step(world, dt=1 / 60)
        if player.on_ground:
            break

    assert player.on_ground is True
    assert player.health < player.max_health


def _grounded_player(y_offset_tiles: int = 5):
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - y_offset_tiles) * TILE_SIZE)
    for _ in range(300):
        player.physics_step(world, dt=1 / 60)
        if player.on_ground:
            break
    assert player.on_ground is True
    return world, player


def test_double_jump_allows_a_second_jump_while_airborne():
    world, player = _grounded_player()

    player.jump()
    assert player.y_vel == PLAYER_JUMP_VELOCITY
    assert player.jump_count == 1
    assert player.double_jump_visual_timer == 0.0  # first jump isn't the "double" one

    player.physics_step(world, dt=1 / 60)  # airborne now, gravity nudges y_vel
    player.jump()
    assert player.y_vel == PLAYER_DOUBLE_JUMP_VELOCITY
    assert player.jump_count == 2
    assert player.double_jump_visual_timer == PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S


def test_cannot_jump_more_than_player_max_jumps():
    assert PLAYER_MAX_JUMPS == 2  # this test's math assumes exactly one double jump
    world, player = _grounded_player()

    player.jump()
    player.physics_step(world, dt=1 / 60)
    player.jump()
    y_vel_after_double_jump = player.y_vel

    player.jump()  # third jump: no jumps left, must be a no-op

    assert player.jump_count == 2
    assert player.y_vel == y_vel_after_double_jump


def test_jump_count_resets_after_landing():
    world, player = _grounded_player()
    player.jump()
    player.jump()
    assert player.jump_count == 2

    for _ in range(300):
        player.physics_step(world, dt=1 / 60)
        if player.on_ground:
            break

    assert player.on_ground is True
    assert player.jump_count == 0


def test_player_respawns_after_death():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 5) * TILE_SIZE)

    player.take_damage(player.max_health + 50)
    assert player.alive is True  # respawn happens immediately in die()
    assert player.health == player.max_health
    assert player.x == player.spawn_x
    assert player.y == player.spawn_y


# --- camera ---

def test_camera_follow_clamps_to_world_bounds():
    camera = Camera()
    huge_x = WORLD_WIDTH_TILES * TILE_SIZE * 10
    for _ in range(500):
        camera.follow(huge_x, 0)
    max_x = WORLD_WIDTH_TILES * TILE_SIZE - camera.view_width
    assert camera.x <= max_x + 1e-6
    assert camera.x >= 0


def test_camera_zoom_bounds():
    from game.settings import CAMERA_MIN_ZOOM, CAMERA_MAX_ZOOM
    camera = Camera()
    for _ in range(100):
        camera.zoom_out()
    assert camera.zoom >= CAMERA_MIN_ZOOM
    for _ in range(100):
        camera.zoom_in()
    assert camera.zoom <= CAMERA_MAX_ZOOM


# --- chunk loading ---

def test_chunks_load_and_unload_around_player():
    world = World(DEFAULT_SEED)
    center_x = WORLD_WIDTH_TILES // 2
    world.ensure_chunks_around(center_x * TILE_SIZE)
    assert len(world.chunks) > 0

    far_x = 5 * TILE_SIZE
    world.ensure_chunks_around(far_x)
    center_chunk = world.chunk_index_for(center_x)
    assert center_chunk not in world.chunks  # unloaded once far away


# --- full app boot (catches rendering/input wiring crashes) ---

def test_game_app_boots_and_steps_headlessly():
    from game.core.game_app import GameApp
    app = GameApp(seed=DEFAULT_SEED)
    try:
        for _ in range(10):
            app.step(dt=1 / 60)
    finally:
        pygame.quit()
