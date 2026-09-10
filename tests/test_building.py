"""Headless tests for the user-requested construction system: Doors
(game/world/doors.py), Beds + shelter detection (game/world/beds.py,
shelter.py), and WorldClock.skip_to_morning -- plus the real T-key click
path through InputHandler for both.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, DAY_LENGTH_S,
    MORNING_TIME_OF_DAY_FRACTION, SHELTER_MAX_AIR_TILES, SLEEP_FADE_DURATION_S,
)
from game.core.world_clock import WorldClock
from game.entities.player import Player
from game.items import item_registry
from game.crafting import recipe_registry
from game.world import doors, beds, shelter
from game.world.world import World
from game.world.tile_registry import (
    AIR_ID, STONE_ID, DOOR_CLOSED_ID, DOOR_OPEN_ID, BED_ID,
)
import game.world.tile_registry as tile_registry


def _carve_room(world, x0, y0, width, height, wall_id=STONE_ID):
    """A solid box border with an open interior, top-left corner (x0, y0)."""
    for dx in range(width):
        for dy in range(height):
            x, y = x0 + dx, y0 + dy
            is_border = dx in (0, width - 1) or dy in (0, height - 1)
            world.set_tile(x, y, wall_id if is_border else AIR_ID)


def _make_player_at(world, x_tile, y_tile=None):
    if y_tile is None:
        surface_y = world.surface_spawn_y(x_tile) + 1
        y_tile = surface_y - 1
    return Player(x_tile * TILE_SIZE, y_tile * TILE_SIZE)


# --- items / recipes ---

def test_door_and_bed_items_and_recipes_are_registered():
    door_item = item_registry.get("door")
    assert door_item.places_tile_id == DOOR_CLOSED_ID
    bed_item = item_registry.get("bed")
    assert bed_item.places_tile_id == BED_ID

    assert recipe_registry.get("door").result_item_id == "door"
    assert recipe_registry.get("bed").result_item_id == "bed"


def test_door_closed_is_solid_and_open_is_not():
    assert tile_registry.get(DOOR_CLOSED_ID).solid is True
    assert tile_registry.get(DOOR_OPEN_ID).solid is False


def test_bed_is_not_solid_like_a_checkpoint():
    assert tile_registry.get(BED_ID).solid is False


# --- doors.toggle ---

def test_toggle_swaps_a_closed_door_to_open_and_back():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    y = world.surface_height_at(x)
    world.set_tile(x, y, DOOR_CLOSED_ID)

    doors.toggle(world, x, y)
    assert world.get_tile(x, y) == DOOR_OPEN_ID
    assert not world.is_solid(x, y)

    doors.toggle(world, x, y)
    assert world.get_tile(x, y) == DOOR_CLOSED_ID
    assert world.is_solid(x, y)


def test_toggle_on_a_non_door_tile_does_nothing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    y = world.surface_height_at(x)
    world.set_tile(x, y, STONE_ID)

    doors.toggle(world, x, y)
    assert world.get_tile(x, y) == STONE_ID


# --- shelter.is_enclosed ---

def test_is_enclosed_true_inside_a_small_sealed_room():
    world = World(DEFAULT_SEED)
    x0, y0 = WORLD_WIDTH_TILES // 2, 60
    _carve_room(world, x0, y0, 7, 5)
    assert shelter.is_enclosed(world, x0 + 3, y0 + 2) is True


def test_is_enclosed_false_out_in_the_open():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    assert shelter.is_enclosed(world, x, surface_y - 3) is False  # open sky above the surface


def test_is_enclosed_false_when_the_room_leaks_through_a_gap():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)
    width, height = 7, 5
    x0, y0 = x - width // 2, surface_y - 15  # well above ground, in open sky
    # Floor + side walls, but no roof row -- directly open to the sky
    # above, which is contiguous across the whole (huge) world width and
    # so will blow well past SHELTER_MAX_AIR_TILES.
    for dx in range(width):
        for dy in range(height):
            xx, yy = x0 + dx, y0 + dy
            is_wall = dx in (0, width - 1) or dy == height - 1
            world.set_tile(xx, yy, STONE_ID if is_wall else AIR_ID)
    assert shelter.is_enclosed(world, x0 + 3, y0 + 2) is False


def test_is_enclosed_false_when_the_room_is_too_big():
    world = World(DEFAULT_SEED)
    x0, y0 = WORLD_WIDTH_TILES // 2, 60
    side = 25  # interior alone is (side-2)^2 = 529 air tiles, well past SHELTER_MAX_AIR_TILES
    assert (side - 2) ** 2 > SHELTER_MAX_AIR_TILES
    _carve_room(world, x0, y0, side, side)
    assert shelter.is_enclosed(world, x0 + side // 2, y0 + side // 2) is False


def test_is_enclosed_false_when_starting_point_is_solid():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    y = world.surface_height_at(x)
    world.set_tile(x, y, STONE_ID)
    assert shelter.is_enclosed(world, x, y) is False


# --- WorldClock.skip_to_morning ---

def test_skip_to_morning_from_the_afternoon_advances_the_day_count():
    clock = WorldClock()
    dawn = DAY_LENGTH_S * MORNING_TIME_OF_DAY_FRACTION
    clock.time_of_day = dawn + 10.0  # just past dawn -- "later today"
    starting_day = clock.day_count

    clock.skip_to_morning()
    assert clock.time_of_day == dawn
    assert clock.day_count == starting_day + 1
    assert clock.is_night is False


def test_skip_to_morning_before_dawn_stays_on_the_same_day():
    clock = WorldClock()
    dawn = DAY_LENGTH_S * MORNING_TIME_OF_DAY_FRACTION
    clock.time_of_day = max(0.0, dawn - 10.0)  # just before dawn, same day
    starting_day = clock.day_count

    clock.skip_to_morning()
    assert clock.time_of_day == dawn
    assert clock.day_count == starting_day


def test_skip_to_morning_always_moves_time_forward_never_backward():
    clock = WorldClock()
    for fraction in (0.0, 0.1, 0.3, 0.5, 0.8, 0.99):
        clock.time_of_day = DAY_LENGTH_S * fraction
        before = (clock.day_count, clock.time_of_day)
        clock.skip_to_morning()
        after = (clock.day_count, clock.time_of_day)
        assert after >= before


# --- beds.try_sleep ---

def test_try_sleep_fails_during_the_day():
    world = World(DEFAULT_SEED)
    clock = WorldClock()
    clock.time_of_day = DAY_LENGTH_S * 0.5  # noon
    assert clock.is_night is False
    x0, y0 = WORLD_WIDTH_TILES // 2, 60
    _carve_room(world, x0, y0, 7, 5)

    reason = beds.try_sleep(world, clock, x0 + 3, y0 + 2)
    assert reason == "You can only sleep at night"


def test_try_sleep_fails_at_night_without_shelter():
    world = World(DEFAULT_SEED)
    clock = WorldClock()
    clock.time_of_day = 0.0  # midnight
    assert clock.is_night is True
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_height_at(x)

    reason = beds.try_sleep(world, clock, x, surface_y - 3)
    assert reason == "This isn't a safe, enclosed shelter"


def test_try_sleep_succeeds_at_night_inside_shelter_and_skips_to_morning():
    world = World(DEFAULT_SEED)
    clock = WorldClock()
    clock.time_of_day = 0.0  # midnight
    x0, y0 = WORLD_WIDTH_TILES // 2, 60
    _carve_room(world, x0, y0, 7, 5)

    reason = beds.try_sleep(world, clock, x0 + 3, y0 + 2)
    assert reason is None
    assert clock.is_night is False
    assert clock.time_of_day == DAY_LENGTH_S * MORNING_TIME_OF_DAY_FRACTION


# --- real T-key click path through InputHandler ---

def test_pressing_t_near_a_closed_door_opens_it_through_game_app():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False

        x = int(app.player.center_x // TILE_SIZE) + 1
        y = int(app.player.center_y // TILE_SIZE)
        app.world.set_tile(x, y, DOOR_CLOSED_ID)

        app.input_handler._handle_talk(app)
        assert app.world.get_tile(x, y) == DOOR_OPEN_ID

        app.input_handler._handle_talk(app)
        assert app.world.get_tile(x, y) == DOOR_CLOSED_ID
    finally:
        pygame.quit()


def test_pressing_t_near_a_bed_at_night_in_shelter_sleeps_through_game_app():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.world_clock.time_of_day = 0.0  # midnight

        px = int(app.player.center_x // TILE_SIZE)
        py = int(app.player.center_y // TILE_SIZE)
        _carve_room(app.world, px - 3, py - 2, 7, 5)
        app.world.set_tile(px, py, BED_ID)
        app.player.x, app.player.y = px * TILE_SIZE, py * TILE_SIZE

        app.input_handler._handle_talk(app)

        assert app.world_clock.is_night is False
        assert app.sleep_fade_remaining_s == SLEEP_FADE_DURATION_S
        app.notifications.update(0.0)  # promote the queued push() to current_text
        assert app.notifications.current_text is not None
    finally:
        pygame.quit()


def test_pressing_t_near_a_bed_during_the_day_does_not_skip_time():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.world_clock.time_of_day = DAY_LENGTH_S * 0.5  # noon

        px = int(app.player.center_x // TILE_SIZE)
        py = int(app.player.center_y // TILE_SIZE)
        _carve_room(app.world, px - 3, py - 2, 7, 5)
        app.world.set_tile(px, py, BED_ID)
        app.player.x, app.player.y = px * TILE_SIZE, py * TILE_SIZE

        starting_time = app.world_clock.time_of_day
        app.input_handler._handle_talk(app)
        assert app.world_clock.time_of_day == starting_time
        assert app.sleep_fade_remaining_s == 0.0
    finally:
        pygame.quit()


def test_game_app_renders_a_door_bed_and_sleep_fade_without_crashing():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False

        x = int(app.player.center_x // TILE_SIZE) + 2
        y = int(app.player.center_y // TILE_SIZE)
        app.world.set_tile(x, y, DOOR_CLOSED_ID)
        app.world.set_tile(x + 2, y, BED_ID)
        app.sleep_fade_remaining_s = SLEEP_FADE_DURATION_S

        app.step(dt=1 / 60)  # must not raise
    finally:
        pygame.quit()
