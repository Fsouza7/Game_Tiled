"""Headless tests for Phase 7 save/load (game/core/save_system.py)."""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH, CHUNK_UNLOAD_RADIUS
from game.core import save_system
from game.core.world_clock import WorldClock
from game.crafting.furnace_system import FurnaceManager, FurnaceJob
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import WORKBENCH_ID


def _make_world_and_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x)
    player = Player(x * TILE_SIZE, surface_y * TILE_SIZE)
    return world, player, x, surface_y


def test_round_trip_preserves_player_state():
    world, player, x, surface_y = _make_world_and_player()
    player.health = 42.0
    player.inventory.add_item("wood", 7)
    player.inventory.select_hotbar(3)
    player.equipment.slots["head"] = "wood_helmet"
    player.discovered_item_ids.add("iron_bar")
    player.skills.add_xp("attack", 5000.0)
    player.skills.try_unlock_node("attack_keen_edge")
    world_clock = WorldClock()
    world_clock.time_of_day = 123.0
    world_clock.day_count = 4
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    world2, player2, world_clock2, furnace_manager2 = save_system.deserialize(data)

    assert world2.seed == world.seed
    assert player2.x == player.x and player2.y == player.y
    assert player2.health == 42.0
    assert player2.character_id == player.character_id
    assert any(s.item_id == "wood" and s.quantity == 7 for s in player2.inventory.slots)
    assert player2.inventory.selected_hotbar_index == 3
    assert player2.equipment.slots["head"] == "wood_helmet"
    assert "iron_bar" in player2.discovered_item_ids
    assert player2.skills.xp("attack") == player.skills.xp("attack")
    assert player2.skills.has_node("attack_keen_edge")
    assert world_clock2.time_of_day == 123.0
    assert world_clock2.day_count == 4


def test_round_trip_preserves_furnace_jobs():
    world, player, x, surface_y = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    furnace_manager.jobs[(x, surface_y)] = FurnaceJob(
        bar_item_id="iron_bar", quantity=2, remaining_s=1.5, total_s=4.0,
    )

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    _, _, _, furnace_manager2 = save_system.deserialize(data)

    job = furnace_manager2.jobs[(x, surface_y)]
    assert job.bar_item_id == "iron_bar"
    assert job.quantity == 2
    assert job.remaining_s == 1.5
    assert job.total_s == 4.0


def test_round_trip_preserves_furnace_input_hoppers():
    """The furnace queue's deposited ore/fuel (FurnaceManager.inputs) must
    survive a save/load same as an in-progress job -- otherwise saving
    mid-queue would silently discard whatever stack the player left
    smelting."""
    from game.crafting.furnace_system import FURNACE_FUEL_SLOT, FURNACE_ORE_SLOT

    world, player, x, surface_y = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    pos = (x, surface_y)
    furnace_manager.input_at(pos)  # create the hopper
    storage = furnace_manager.inputs[pos]
    storage.slots[FURNACE_FUEL_SLOT].item_id = "coal"
    storage.slots[FURNACE_FUEL_SLOT].quantity = 6
    storage.slots[FURNACE_ORE_SLOT].item_id = "iron_ore"
    storage.slots[FURNACE_ORE_SLOT].quantity = 9

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    _, _, _, furnace_manager2 = save_system.deserialize(data)

    storage2 = furnace_manager2.input_at(pos)
    assert storage2.slots[FURNACE_FUEL_SLOT].item_id == "coal"
    assert storage2.slots[FURNACE_FUEL_SLOT].quantity == 6
    assert storage2.slots[FURNACE_ORE_SLOT].item_id == "iron_ore"
    assert storage2.slots[FURNACE_ORE_SLOT].quantity == 9


def test_round_trip_preserves_an_in_progress_craft_job():
    from game.crafting.crafting_system import CraftJob

    world, player, x, surface_y = _make_world_and_player()
    player.craft_job = CraftJob(recipe_id="wood_plank_block", remaining_s=0.3, total_s=0.4)
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    _, player2, _, _ = save_system.deserialize(data)

    assert player2.craft_job.recipe_id == "wood_plank_block"
    assert player2.craft_job.remaining_s == 0.3
    assert player2.craft_job.total_s == 0.4


def test_old_save_without_craft_job_field_loads_with_none():
    world, player, x, surface_y = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    del data["player"]["craft_job"]

    _, player2, _, _ = save_system.deserialize(data)
    assert player2.craft_job is None


def test_no_pending_craft_round_trips_as_none():
    world, player, x, surface_y = _make_world_and_player()
    assert player.craft_job is None
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    assert data["player"]["craft_job"] is None
    _, player2, _, _ = save_system.deserialize(data)
    assert player2.craft_job is None


def test_only_dirty_chunks_are_saved():
    world, player, x, surface_y = _make_world_and_player()
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    # Load a neighboring chunk without mutating it -- it must not appear.
    world.get_or_create_chunk(world.chunk_index_for(x) + 1)
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    assert data["dirty_chunks"] == []

    world.try_break_tile(x, surface_y + 1)
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    assert len(data["dirty_chunks"]) == 1
    assert data["dirty_chunks"][0]["chunk_x"] == world.chunk_index_for(x)


def test_a_modified_tile_round_trips_exactly_and_the_rest_of_the_chunk_matches_baseline():
    world, player, x, surface_y = _make_world_and_player()
    world.try_break_tile(x, surface_y + 1)  # mine one dirt tile to AIR
    world.try_place_tile(x, surface_y - 1, WORKBENCH_ID)
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()

    data = save_system.serialize(world, player, world_clock, furnace_manager)
    world2, _, _, _ = save_system.deserialize(data)

    chunk_x = world.chunk_index_for(x)
    base_x = chunk_x * 32
    for local_x in range(32):
        wx = base_x + local_x
        if wx >= WORLD_WIDTH_TILES:
            break
        original = world.get_or_create_chunk(chunk_x).tiles[local_x]
        restored = world2.get_or_create_chunk(chunk_x).tiles[local_x]
        assert original == restored, f"column {wx} mismatch after round-trip"


def test_edits_survive_the_chunk_unloading_before_a_save():
    """Regression test: World._unload_far_chunks used to just `del` a
    chunk once the player wandered CHUNK_UNLOAD_RADIUS chunks away, with
    no record kept of what had changed in it -- so mining/building near
    spawn, then exploring far enough away, then saving, silently lost
    those edits forever (not just from live memory -- the save itself
    never saw them, since serialize() only ever looked at world.chunks,
    which no longer had the chunk in it at all)."""
    world, player, x, surface_y = _make_world_and_player()
    world.try_break_tile(x, surface_y + 1)  # mine one dirt tile to AIR
    assert world.chunk_index_for(x) in world.chunks

    far_x = x + (CHUNK_UNLOAD_RADIUS + 3) * CHUNK_WIDTH
    world.ensure_chunks_around(far_x * TILE_SIZE)
    assert world.chunk_index_for(x) not in world.chunks  # actually unloaded, not a no-op

    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    data = save_system.serialize(world, player, world_clock, furnace_manager)
    assert len(data["dirty_chunks"]) == 1

    world2, _, _, _ = save_system.deserialize(data)
    from game.world.tile_registry import AIR_ID
    assert world2.get_tile(x, surface_y + 1) == AIR_ID


def test_edits_survive_walking_away_and_back_without_saving():
    world, player, x, surface_y = _make_world_and_player()
    world.try_break_tile(x, surface_y + 1)
    from game.world.tile_registry import AIR_ID

    far_x = x + (CHUNK_UNLOAD_RADIUS + 3) * CHUNK_WIDTH
    world.ensure_chunks_around(far_x * TILE_SIZE)
    assert world.chunk_index_for(x) not in world.chunks

    world.ensure_chunks_around(x * TILE_SIZE)  # walk back, no save/load involved
    assert world.get_tile(x, surface_y + 1) == AIR_ID
    assert world.get_or_create_chunk(world.chunk_index_for(x)).dirty


def test_save_to_file_and_load_from_file_round_trip(tmp_path):
    world, player, x, surface_y = _make_world_and_player()
    world.try_break_tile(x, surface_y + 1)
    world_clock = WorldClock()
    furnace_manager = FurnaceManager()
    path = str(tmp_path / "nested" / "save.json")

    save_system.save_to_file(world, player, world_clock, furnace_manager, path)
    assert save_system.save_exists(path)

    data = save_system.load_from_file(path)
    world2, player2, _, _ = save_system.deserialize(data)
    assert world2.seed == world.seed
    assert world2.get_tile(x, surface_y + 1) == world.get_tile(x, surface_y + 1)


def test_load_from_file_missing_path_returns_none(tmp_path):
    missing = str(tmp_path / "does_not_exist.json")
    assert save_system.load_from_file(missing) is None


def test_pause_menu_save_and_load_round_trip_through_game_app(tmp_path, monkeypatch):
    """End-to-end through the real pause-menu click path (InputHandler ->
    GameApp.save_game/load_game), not just the pure serialize/deserialize
    functions -- catches wiring mistakes (wrong action name, wrong
    button rect) that a unit test of save_system alone wouldn't."""
    from game.core.game_app import GameApp
    from game.rendering.renderer import pause_menu_button_rects

    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "save.json"))

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.paused = True
        app.player.health = 33.0
        app.player.inventory.add_item("wood", 4)

        save_rect = pause_menu_button_rects(settings_open=False)["save"]
        app.input_handler._handle_pause_click(save_rect.center, app)
        assert save_system.save_exists(save_system.SAVE_FILE_PATH)

        app.player.health = 100.0  # mutate after saving, to prove load restores it

        load_rect = pause_menu_button_rects(settings_open=False)["load"]
        app.input_handler._handle_pause_click(load_rect.center, app)

        assert app.player.health == 33.0
        assert any(s.item_id == "wood" and s.quantity == 4 for s in app.player.inventory.slots)
    finally:
        pygame.quit()


def test_game_app_boots_on_title_screen_not_character_select():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        assert app.title_open is True
        assert app.character_select_open is False
        assert app.class_select_open is False
        for _ in range(3):
            app.step(dt=1 / 60)
        assert app.title_open is True
    finally:
        pygame.quit()


def test_title_new_game_opens_character_select(tmp_path, monkeypatch):
    from game.core.game_app import GameApp
    from game.rendering.renderer import title_button_rects

    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "save.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        new_pos = title_button_rects()["new"].center
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=new_pos)
        app.input_handler.handle_discrete_events([click], app)
        assert app.title_open is False
        assert app.character_select_open is True
        assert app.class_select_open is False
    finally:
        pygame.quit()


def test_title_continue_without_save_is_a_noop(tmp_path, monkeypatch):
    from game.core.game_app import GameApp
    from game.rendering.renderer import title_button_rects

    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "missing.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        continue_pos = title_button_rects()["continue"].center
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=continue_pos)
        app.input_handler.handle_discrete_events([click], app)
        assert app.title_open is True
        assert app.character_select_open is False
    finally:
        pygame.quit()


def test_title_continue_loads_save_and_skips_select_screens(tmp_path, monkeypatch):
    from game.core.game_app import GameApp
    from game.rendering.renderer import title_button_rects

    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "save.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.player.health = 33.0
        app.save_game()
        app.player.health = 100.0

        continue_pos = title_button_rects()["continue"].center
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=continue_pos)
        app.input_handler.handle_discrete_events([click], app)

        assert app.title_open is False
        assert app.character_select_open is False
        assert app.class_select_open is False
        assert app.player.health == 33.0
    finally:
        pygame.quit()
