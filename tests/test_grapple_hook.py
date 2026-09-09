"""Headless tests for the Grapple Hook accessory: the new "accessory"
equipment slot, the I/E keybind swap (I = inventory, E = use accessory),
the wall-raycast helper, and the hook's pull/cling/release physics.
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH, GRAPPLE_COOLDOWN_S
from game.entities.player import Player
from game.entities import grapple
from game.items import item_registry
from game.items.item import ItemCategory
from game.crafting import recipe_registry
from game.inventory.equipment import SLOTS as EQUIPMENT_SLOTS
from game.world.world import World
from game.world.tile_registry import STONE_ID, AIR_ID


def _air_world_and_player():
    """A player high above the surface in open air, same "keeps terrain
    out of the way" precedent used by the Summoner/skills tests."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    air_y = (world.surface_spawn_y(x) - 10) * TILE_SIZE
    player = Player(x * TILE_SIZE, air_y)
    return world, player, x, air_y


def _place_wall(world, tile_x, tile_y):
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, STONE_ID)


def _equip_hook(player):
    if player.equipment.get("accessory") == "grapple_hook":
        return
    player.inventory.add_item("grapple_hook", 1)
    assert player.equipment.equip_from_inventory(player.inventory, "grapple_hook") is True


# --- registry sanity ---

def test_accessory_slot_exists():
    assert "accessory" in EQUIPMENT_SLOTS


def test_grapple_hook_item_is_a_proper_accessory():
    item_def = item_registry.get("grapple_hook")
    assert item_def.category == ItemCategory.ACCESSORY
    assert item_def.equip_slot == "accessory"
    assert item_def.accessory_kind == "grapple_hook"


def test_grapple_hook_recipe_is_registered():
    recipe = recipe_registry.get("grapple_hook")
    assert recipe.result_item_id == "grapple_hook"


# --- raycast helper ---

def test_find_hook_anchor_finds_a_wall_in_range():
    world, player, x, air_y = _air_world_and_player()
    wall_tile_x = x + 3
    wall_tile_y = int(air_y // TILE_SIZE)
    _place_wall(world, wall_tile_x, wall_tile_y)

    anchor = grapple.find_hook_anchor(world, player.center_x, player.center_y, 1.0, 0.0)

    assert anchor is not None
    anchor_x, anchor_y = anchor
    assert anchor_x < wall_tile_x * TILE_SIZE  # stops just short of the wall, not inside it
    assert not world.is_solid(int(anchor_x // TILE_SIZE), int(anchor_y // TILE_SIZE))


def test_find_hook_anchor_returns_none_with_nothing_in_range():
    world, player, x, air_y = _air_world_and_player()
    # No wall placed anywhere nearby -- open sky in every direction.
    anchor = grapple.find_hook_anchor(world, player.center_x, player.center_y, 1.0, 0.0)
    assert anchor is None


# --- Player.try_use_accessory ---

def test_try_use_accessory_does_nothing_with_no_accessory_equipped():
    world, player, x, air_y = _air_world_and_player()
    player.equipment.unequip_to_inventory(player.inventory, "accessory")
    assert player.try_use_accessory(world, (player.center_x + 100, player.center_y)) is False
    assert player.hook_target is None


def test_try_use_accessory_misses_with_nothing_in_range():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    fired = player.try_use_accessory(world, (player.center_x + 100, player.center_y))
    assert fired is False
    assert player.hook_target is None
    assert player.hook_cooldown_remaining > 0.0  # still costs a cooldown, even on a miss


def test_try_use_accessory_catches_a_wall_and_toggling_again_releases_it():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    wall_tile_x = x + 3
    _place_wall(world, wall_tile_x, int(air_y // TILE_SIZE))

    fired = player.try_use_accessory(world, (player.center_x + 1000, player.center_y))
    assert fired is True
    assert player.hook_target is not None

    released = player.try_use_accessory(world, (player.center_x + 1000, player.center_y))
    assert released is True
    assert player.hook_target is None


def test_hook_fire_is_throttled_by_cooldown():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    # Two misses back to back -- the second should be blocked by the
    # cooldown from the first, not attempt (and fail) independently.
    player.try_use_accessory(world, (player.center_x + 100, player.center_y))
    cooldown_after_first = player.hook_cooldown_remaining
    fired_again = player.try_use_accessory(world, (player.center_x + 100, player.center_y))
    assert fired_again is False
    assert player.hook_cooldown_remaining == cooldown_after_first  # untouched -- the call was a no-op


# --- pull/cling/release physics ---

def test_hooked_player_is_pulled_toward_the_anchor_and_gravity_is_suspended():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    wall_tile_x = x + 3
    _place_wall(world, wall_tile_x, int(air_y // TILE_SIZE))
    player.try_use_accessory(world, (player.center_x + 1000, player.center_y))
    assert player.hook_target is not None

    start_x, start_y = player.center_x, player.center_y
    for _ in range(30):
        player.physics_step(world, dt=1 / 60)

    # Pulled meaningfully to the right, toward the wall...
    assert player.center_x > start_x + TILE_SIZE
    # ...and NOT dropped by gravity while the hook is active (a real fall
    # over 30 frames at GRAVITY=0.7/frame^2 would be tens of pixels).
    assert abs(player.center_y - start_y) < TILE_SIZE


def test_jumping_while_hooked_releases_it_and_grants_a_full_jump():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    wall_tile_x = x + 3
    _place_wall(world, wall_tile_x, int(air_y // TILE_SIZE))
    player.try_use_accessory(world, (player.center_x + 1000, player.center_y))
    player.jump_count = 2  # simulate having already used both jumps before hooking

    player.jump()

    assert player.hook_target is None
    assert player.jump_count == 1  # one fresh jump consumed, not blocked by the earlier count
    assert player.y_vel < 0  # an actual upward launch, not a no-op


def test_hooked_player_eventually_clings_near_the_wall_without_clipping_through():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    wall_tile_x = x + 2
    wall_tile_y = int(air_y // TILE_SIZE)
    _place_wall(world, wall_tile_x, wall_tile_y)
    player.try_use_accessory(world, (player.center_x + 1000, player.center_y))

    for _ in range(120):
        player.physics_step(world, dt=1 / 60)

    # Held near the wall, not teleported past/through it.
    assert player.center_x < wall_tile_x * TILE_SIZE
    assert wall_tile_x * TILE_SIZE - player.center_x < TILE_SIZE * 1.5


def test_respawn_clears_hook_state():
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    _place_wall(world, x + 3, int(air_y // TILE_SIZE))
    player.try_use_accessory(world, (player.center_x + 1000, player.center_y))
    assert player.hook_target is not None

    player.respawn()

    assert player.hook_target is None
    assert player.hook_cooldown_remaining == 0.0


# --- InputHandler keybind wiring ---

def test_i_key_toggles_inventory_not_e():
    from game.input.input_handler import InputHandler
    from game.core.camera import Camera

    class _FakeGameApp:
        def __init__(self, player, world):
            self.player = player
            self.world = world
            self.inventory_open = False
            self.crafting_open = False
            self.skills_open = False
            self.paused = False
            self.settings_open = False
            self.camera = Camera()

    # pygame.mouse.get_pos() (used by the new E/use-accessory handler)
    # needs an initialized display even under the dummy SDL driver.
    pygame.display.set_mode((1, 1))
    world, player, _, _ = _air_world_and_player()
    app = _FakeGameApp(player, world)
    handler = InputHandler()

    e_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
    handler._handle_keydown(e_event, app)
    assert app.inventory_open is False  # E no longer opens inventory

    i_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i)
    handler._handle_keydown(i_event, app)
    assert app.inventory_open is True


def test_e_key_fires_the_equipped_hook():
    from game.input.input_handler import InputHandler
    from game.core.camera import Camera

    class _FakeGameApp:
        def __init__(self, player, world):
            self.player = player
            self.world = world
            self.paused = False
            self.camera = Camera()

    pygame.display.set_mode((1, 1))
    world, player, x, air_y = _air_world_and_player()
    _equip_hook(player)
    _place_wall(world, x + 3, int(air_y // TILE_SIZE))
    app = _FakeGameApp(player, world)
    app.camera.x = player.center_x - app.camera.view_width / 2
    app.camera.y = player.center_y - app.camera.view_height / 2

    # Mouse position doesn't matter for this headless check -- what
    # matters is that the E handler reaches Player.try_use_accessory at
    # all; the aim-direction math itself is covered by the
    # raycast/try_use_accessory tests above.
    e_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
    InputHandler()._handle_keydown(e_event, app)

    assert player.hook_cooldown_remaining > 0.0  # the accessory was actually invoked


# --- full GameApp smoke test ---

def test_game_app_equip_and_fire_hook_through_real_input_and_render():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.character_select_open = False
        app.class_select_open = False

        player = app.player
        player.inventory.add_item("grapple_hook", 1)
        hook_slot = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "grapple_hook")
        # Equip via the real click path (I now opens inventory).
        i_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i)
        app.input_handler.handle_discrete_events([i_event], app)
        assert app.inventory_open is True

        from game.rendering.renderer import inventory_bag_slot_rect
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=inventory_bag_slot_rect(hook_slot).center)
        app.input_handler.handle_discrete_events([click], app)
        assert player.equipment.get("accessory") == "grapple_hook"

        close = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i)
        app.input_handler.handle_discrete_events([close], app)

        e_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
        app.input_handler.handle_discrete_events([e_event], app)
        app.step(dt=1 / 60)  # a real draw call -- catches any rendering crash from _draw_hook_line
    finally:
        pygame.quit()
