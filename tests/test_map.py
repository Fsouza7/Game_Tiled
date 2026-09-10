"""Headless tests for the full Map screen (M): fog-of-war exploration
tracking (game/world/exploration.py) and its rendering/save round-trip.
"""
import pygame

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    MAP_CELL_SIZE_TILES, MAP_REVEAL_RADIUS_TILES, STRUCTURE_SLOT_WIDTH_TILES,
)
from game.entities.player import Player
from game.world.world import World
from game.world import exploration, structures
from game.world.tile_registry import AIR_ID
from game.core import save_system
from game.core.world_clock import WorldClock
from game.crafting.furnace_system import FurnaceManager


def _find_structure(seed=DEFAULT_SEED, kind=None):
    """Scans slots for a real world-generated structure -- optionally of a
    specific kind -- for tests that need one to actually exist somewhere."""
    slot_count = WORLD_WIDTH_TILES // STRUCTURE_SLOT_WIDTH_TILES
    for slot_index in range(slot_count):
        instance = structures.structure_for_slot(seed, slot_index)
        if instance is not None and (kind is None or instance.kind == kind):
            return instance
    return None


def _make_world_and_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


# --- reveal_around ---

def test_reveal_around_populates_nearby_cells():
    world, player = _make_world_and_player()
    assert world.explored_cells == {}
    world.reveal_map_around(player.center_x, player.center_y)
    assert len(world.explored_cells) > 0

    player_cell = (
        int(player.center_x // TILE_SIZE) // MAP_CELL_SIZE_TILES,
        int(player.center_y // TILE_SIZE) // MAP_CELL_SIZE_TILES,
    )
    assert player_cell in world.explored_cells


def test_reveal_around_does_not_reveal_cells_far_outside_the_radius():
    world, player = _make_world_and_player()
    world.reveal_map_around(player.center_x, player.center_y)
    far_cell = (
        int(player.center_x // TILE_SIZE) // MAP_CELL_SIZE_TILES + (MAP_REVEAL_RADIUS_TILES // MAP_CELL_SIZE_TILES) * 10,
        int(player.center_y // TILE_SIZE) // MAP_CELL_SIZE_TILES,
    )
    assert far_cell not in world.explored_cells


def test_reveal_around_is_idempotent_and_only_grows():
    world, player = _make_world_and_player()
    world.reveal_map_around(player.center_x, player.center_y)
    first_count = len(world.explored_cells)
    world.reveal_map_around(player.center_x, player.center_y)
    assert len(world.explored_cells) == first_count


def test_moving_reveals_new_cells_further_along():
    world, player = _make_world_and_player()
    world.reveal_map_around(player.center_x, player.center_y)
    before = set(world.explored_cells)

    far_x = player.center_x + MAP_REVEAL_RADIUS_TILES * 4 * TILE_SIZE
    world.reveal_map_around(far_x, player.center_y)
    after = set(world.explored_cells)

    assert after - before, "walking further should reveal cells that weren't visible before"


def test_cell_color_distinguishes_sky_air_solid_and_cave_air():
    world, player = _make_world_and_player()
    surface_tile_x = int(player.center_x // TILE_SIZE)
    surface_y = world.surface_height_at(surface_tile_x)

    sky_color = exploration._cell_color(world, surface_tile_x, surface_y - 5)
    ground_color = exploration._cell_color(world, surface_tile_x, surface_y)
    cave_color = exploration._cell_color(world, surface_tile_x, surface_y + 40)

    assert sky_color == exploration.SKY_COLOR
    assert ground_color != exploration.SKY_COLOR
    assert ground_color != (0, 0, 0)  # not the raw AIR_ID color -- must resolve to the actual solid tile's color
    # Deep enough underground with no light source nearby should read as cave air, not sky.
    assert world.get_tile(surface_tile_x, surface_y + 40) == AIR_ID or cave_color != exploration.SKY_COLOR


# --- T/M priority and toggling (through the real InputHandler) ---

def test_m_opens_and_closes_the_map_and_closes_other_screens():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.inventory_open = True

        keydown = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)
        app.input_handler.handle_discrete_events([keydown], app)
        assert app.map_open is True
        assert app.inventory_open is False

        app.input_handler.handle_discrete_events([keydown], app)
        assert app.map_open is False
    finally:
        pygame.quit()


def test_opening_inventory_closes_the_map():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.map_open = True

        keydown = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i)
        app.input_handler.handle_discrete_events([keydown], app)
        assert app.inventory_open is True
        assert app.map_open is False
    finally:
        pygame.quit()


def test_game_app_step_reveals_cells_around_the_player():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        assert app.world.explored_cells == {}
        for _ in range(5):
            app.step(dt=1 / 60)
        assert len(app.world.explored_cells) > 0
    finally:
        pygame.quit()


# --- save/load ---

def test_explored_cells_round_trip_through_save():
    world, player = _make_world_and_player()
    world.reveal_map_around(player.center_x, player.center_y)
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    world2, _, _, _ = save_system.deserialize(data)

    assert world2.explored_cells == world.explored_cells


def test_old_save_without_explored_cells_field_loads_with_empty_map():
    world, player = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    del data["explored_cells"]
    world2, _, _, _ = save_system.deserialize(data)
    assert world2.explored_cells == {}


# --- structure markers ---

def test_discovered_structures_finds_a_structure_once_its_anchor_cell_is_explored():
    from game.rendering.renderer import _discovered_structures

    instance = _find_structure()
    assert instance is not None, "no structure found in the first N slots -- widen the scan or check the seed"

    world = World(DEFAULT_SEED)
    world.reveal_map_around(instance.anchor_x * TILE_SIZE, instance.anchor_y * TILE_SIZE)

    min_cx = min(c[0] for c in world.explored_cells)
    max_cx = max(c[0] for c in world.explored_cells)
    found = _discovered_structures(world, min_cx, max_cx)
    assert any(f.anchor_x == instance.anchor_x and f.anchor_y == instance.anchor_y and f.kind == instance.kind for f in found)


def test_discovered_structures_excludes_an_unexplored_structure():
    from game.rendering.renderer import _discovered_structures

    instance = _find_structure()
    assert instance is not None

    world = World(DEFAULT_SEED)
    # Reveal somewhere far away instead of near the structure itself.
    world.reveal_map_around((instance.anchor_x + WORLD_WIDTH_TILES // 4) * TILE_SIZE, 0)

    if world.explored_cells:
        min_cx = min(c[0] for c in world.explored_cells)
        max_cx = max(c[0] for c in world.explored_cells)
        found = _discovered_structures(world, min_cx, max_cx)
        assert not any(f.anchor_x == instance.anchor_x and f.anchor_y == instance.anchor_y for f in found)


def test_draw_map_structure_marker_does_not_crash_for_every_kind():
    from game.rendering.renderer import Renderer
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    for kind in structures.ALL_KINDS:
        renderer._draw_map_structure_marker(window, kind, (50, 50))


# --- rendering ---

def test_draw_map_screen_does_not_crash_when_empty_or_populated():
    from game.rendering.renderer import Renderer
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    world, player = _make_world_and_player()

    renderer._draw_map_screen(window, world, player)  # nothing explored yet

    world.reveal_map_around(player.center_x, player.center_y)
    renderer._draw_map_screen(window, world, player)


def test_draw_map_screen_with_a_discovered_structure_does_not_crash():
    from game.rendering.renderer import Renderer
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    instance = _find_structure()
    assert instance is not None

    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    world = World(DEFAULT_SEED)
    player = Player(instance.anchor_x * TILE_SIZE, instance.anchor_y * TILE_SIZE)
    world.reveal_map_around(player.center_x, player.center_y)

    renderer._draw_map_screen(window, world, player)
