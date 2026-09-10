"""Headless tests for the F4 debug-mode toggle and its F5-F11 cheats
(GameApp.debug_* methods, game/core/debug_overlay.py, and the real F-key
click path through InputHandler).
"""
import pygame

from game.settings import DEFAULT_SEED, TILE_SIZE, DEBUG_RESTOCK_COINS
from game.entities import enemy_registry
from game.entities.boss import Boss
from game.entities.enemy import Enemy
from game.entities.enemy_def import AIType
from game.items import item_registry


def _new_app():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    app.title_open = False
    app.character_select_open = False
    app.class_select_open = False
    return app


def _press(app, key):
    event = pygame.event.Event(pygame.KEYDOWN, key=key)
    app.input_handler._handle_keydown(event, app)


# --- debug_unlock_all_recipes ---

def test_debug_unlock_all_recipes_discovers_every_item():
    app = _new_app()
    try:
        app.debug_unlock_all_recipes()
        assert app.player.discovered_item_ids == set(item_registry.all_items().keys())
    finally:
        pygame.quit()


# --- debug_reveal_map ---

def test_debug_reveal_map_fills_the_whole_explored_cells_grid():
    app = _new_app()
    try:
        before = len(app.world.explored_cells)
        app.debug_reveal_map()
        after = len(app.world.explored_cells)
        assert after > before
        # A cell far from spawn that reveal_map_around alone would never
        # have touched is now present.
        assert (0, 0) in app.world.explored_cells
    finally:
        pygame.quit()


# --- debug_restock ---

def test_debug_restock_heals_and_grants_coins():
    app = _new_app()
    try:
        app.player.health = 1.0
        starting_coins = app.player.inventory.count_item("coin")
        app.debug_restock()
        assert app.player.health == app.player.max_health
        assert app.player.inventory.count_item("coin") == starting_coins + DEBUG_RESTOCK_COINS
    finally:
        pygame.quit()


# --- debug_spawn_all_bosses / debug_spawn_all_enemies ---

def test_debug_spawn_all_bosses_spawns_exactly_the_registered_bosses():
    app = _new_app()
    try:
        boss_defs = [e for e in enemy_registry.all_enemies() if e.ai_type == AIType.BOSS]
        assert boss_defs  # sanity: at least the Slime King exists
        app.debug_spawn_all_bosses()
        spawned = [e for e in app.enemies if isinstance(e, Boss)]
        assert len(spawned) == len(boss_defs)
        assert {b.enemy_def.id for b in spawned} == {d.id for d in boss_defs}
    finally:
        pygame.quit()


def test_debug_spawn_all_enemies_spawns_exactly_the_non_boss_roster():
    app = _new_app()
    try:
        ground_defs = [e for e in enemy_registry.all_enemies() if e.ai_type != AIType.BOSS]
        app.debug_spawn_all_enemies()
        spawned = [e for e in app.enemies if isinstance(e, Enemy) and not isinstance(e, Boss)]
        assert len(spawned) == len(ground_defs)
        assert {e.enemy_def.id for e in spawned} == {d.id for d in ground_defs}
        assert all(not isinstance(e, Boss) for e in spawned)
    finally:
        pygame.quit()


# --- debug_teleport_to / debug_teleport_to_spawn ---

def test_debug_teleport_to_moves_the_player_and_clears_velocity():
    app = _new_app()
    try:
        app.player.x_vel = 5.0
        app.player.y_vel = -3.0
        app.player.jump_count = 2
        target_x, target_y = 500.0, 700.0
        app.debug_teleport_to(target_x, target_y)
        assert app.player.center_x == target_x
        assert app.player.center_y == target_y
        assert app.player.x_vel == 0.0
        assert app.player.y_vel == 0.0
        assert app.player.jump_count == 0
    finally:
        pygame.quit()


def test_debug_teleport_to_spawn_returns_to_the_spawn_point():
    app = _new_app()
    try:
        app.player.x, app.player.y = 999.0, 999.0
        app.debug_teleport_to_spawn()
        assert app.player.center_x == app.player.spawn_x + app.player.width / 2
        assert app.player.center_y == app.player.spawn_y + app.player.height / 2
    finally:
        pygame.quit()


# --- F4 toggle + gating ---

def test_f4_toggles_debug_mode_and_pushes_a_notification():
    app = _new_app()
    try:
        assert app.debug_mode is False
        _press(app, pygame.K_F4)
        assert app.debug_mode is True
        app.notifications.update(0.0)
        assert app.notifications.current_text == "Debug mode ON"

        _press(app, pygame.K_F4)
        assert app.debug_mode is False
    finally:
        pygame.quit()


def test_debug_cheats_are_no_ops_while_debug_mode_is_off():
    app = _new_app()
    try:
        assert app.debug_mode is False
        starting_discovered = set(app.player.discovered_item_ids)
        _press(app, pygame.K_F5)
        assert app.player.discovered_item_ids == starting_discovered

        starting_enemies = len(app.enemies)
        _press(app, pygame.K_F8)
        _press(app, pygame.K_F9)
        assert len(app.enemies) == starting_enemies
    finally:
        pygame.quit()


def test_f5_through_f9_work_once_debug_mode_is_on():
    app = _new_app()
    try:
        _press(app, pygame.K_F4)  # turn debug mode on
        assert app.debug_mode is True

        _press(app, pygame.K_F5)
        assert app.player.discovered_item_ids == set(item_registry.all_items().keys())

        _press(app, pygame.K_F7)
        assert app.player.inventory.count_item("coin") == DEBUG_RESTOCK_COINS

        _press(app, pygame.K_F8)
        _press(app, pygame.K_F9)
        assert any(isinstance(e, Boss) for e in app.enemies)
        assert any(not isinstance(e, Boss) for e in app.enemies)
    finally:
        pygame.quit()


def test_f10_teleports_to_the_mouse_cursor_world_position(monkeypatch):
    app = _new_app()
    try:
        _press(app, pygame.K_F4)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (300, 200))
        expected_x, expected_y = app.camera.screen_to_world(300, 200)

        _press(app, pygame.K_F10)
        assert abs(app.player.x - (expected_x - app.player.width / 2)) < 1e-6
        assert abs(app.player.y - (expected_y - app.player.height / 2)) < 1e-6
    finally:
        pygame.quit()


def test_f11_teleports_back_to_spawn():
    app = _new_app()
    try:
        _press(app, pygame.K_F4)
        app.player.x, app.player.y = 999.0, 999.0
        _press(app, pygame.K_F11)
        assert app.player.center_x == app.player.spawn_x + app.player.width / 2
        assert app.player.center_y == app.player.spawn_y + app.player.height / 2
    finally:
        pygame.quit()


# --- debug_mode persists across Restart/Load, like prefs ---

def test_debug_mode_survives_restart():
    app = _new_app()
    try:
        _press(app, pygame.K_F4)
        assert app.debug_mode is True
        app.restart()
        assert app.debug_mode is True
    finally:
        pygame.quit()


# --- rendering ---

def test_game_app_renders_the_debug_banner_and_overlay_without_crashing():
    app = _new_app()
    try:
        _press(app, pygame.K_F4)
        app.debug_overlay.enabled = True
        app.debug_spawn_all_bosses()
        app.debug_spawn_all_enemies()
        app.step(dt=1 / 60)  # must not raise
    finally:
        pygame.quit()
