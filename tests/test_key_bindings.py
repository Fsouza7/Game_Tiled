"""Headless tests for rebindable gameplay keys: defaults, persistence,
reserved keys, swap-on-collision, and the Settings click-then-press path.
"""
import json

import pygame  # noqa: F401

from game.settings import DEFAULT_SEED
from game.core import settings_store
from game.input.bindings import (
    BINDABLE_ACTIONS, DEFAULT_BINDINGS, bound_key, extra_arrow_held,
    is_reserved_key, key_from_name, parse_bindings, serialize_bindings,
)
from game.rendering.renderer import (
    pause_button_at_screen_pos, settings_binding_button_rect,
    settings_panel_rect, settings_reset_bindings_rect, settings_row_rect,
)


class _Keys(dict):
    def __getitem__(self, key):
        return super().get(key, False)


def test_every_bindable_action_has_a_default():
    assert {action for action, _label in BINDABLE_ACTIONS} == set(DEFAULT_BINDINGS)


def test_parse_bindings_ignores_unknown_actions_and_bad_names():
    merged = parse_bindings({"inventory": "u", "not_an_action": "q", "jump": "nope"})
    assert merged["inventory"] == pygame.K_u
    assert merged["jump"] == DEFAULT_BINDINGS["jump"]
    assert "not_an_action" not in merged


def test_key_from_name_accepts_letters_and_space():
    assert key_from_name("I") == pygame.K_i
    assert key_from_name("space") == pygame.K_SPACE
    assert key_from_name("") is None


def test_esc_digits_and_function_keys_are_reserved():
    assert is_reserved_key(pygame.K_ESCAPE)
    assert is_reserved_key(pygame.K_5)
    assert is_reserved_key(pygame.K_F4)
    assert not is_reserved_key(pygame.K_i)
    assert not is_reserved_key(pygame.K_SPACE)


def test_extra_arrows_work_until_an_arrow_is_bound():
    prefs = settings_store.Settings()
    keys = _Keys({pygame.K_LEFT: True})
    assert extra_arrow_held(keys, prefs, "move_left") is True

    prefs.bindings["inventory"] = pygame.K_LEFT
    assert extra_arrow_held(keys, prefs, "move_left") is False


def test_old_settings_file_without_bindings_loads_defaults(tmp_path):
    path = str(tmp_path / "settings.json")
    with open(path, "w") as f:
        json.dump({"music_volume": 0.2, "sfx_volume": 0.3}, f)
    prefs = settings_store.load(path)
    assert prefs.bindings["inventory"] == pygame.K_i
    assert prefs.music_volume == 0.2


def test_bindings_round_trip_through_settings_store(tmp_path):
    path = str(tmp_path / "settings.json")
    original = settings_store.Settings(bindings={"inventory": "u", "jump": "w"})
    settings_store.save(original, path)
    loaded = settings_store.load(path)
    assert loaded.bindings["inventory"] == pygame.K_u
    assert loaded.bindings["jump"] == pygame.K_w
    assert loaded.bindings["eat"] == pygame.K_f


def test_set_binding_swaps_with_the_previous_owner(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.set_binding("inventory", pygame.K_e)  # E is use_accessory by default
        assert app.prefs.bindings["inventory"] == pygame.K_e
        assert app.prefs.bindings["use_accessory"] == pygame.K_i  # swapped
        reloaded = settings_store.load(str(tmp_path / "settings.json"))
        assert reloaded.bindings["inventory"] == pygame.K_e
    finally:
        pygame.quit()


def test_clicking_a_key_chip_then_pressing_a_key_rebinds_through_input_handler(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.paused = True
        app.settings_open = True

        inventory_index = next(i for i, (action, _) in enumerate(BINDABLE_ACTIONS) if action == "inventory")
        chip = settings_binding_button_rect(inventory_index)
        assert pause_button_at_screen_pos(chip.center, settings_open=True) == "bind:inventory"
        app.input_handler._handle_pause_click(chip.center, app)
        assert app.rebinding_action == "inventory"

        app.input_handler.handle_discrete_events(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u)], app,
        )
        assert app.rebinding_action is None
        assert app.prefs.bindings["inventory"] == pygame.K_u

        app.settings_open = False
        app.paused = False
        app.input_handler.handle_discrete_events(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u)], app,
        )
        assert app.inventory_open is True
        app.input_handler.handle_discrete_events(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i)], app,
        )
        assert app.inventory_open is True  # old I no longer toggles it
    finally:
        pygame.quit()


def test_reserved_key_while_listening_is_rejected(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.paused = True
        app.settings_open = True
        app.rebinding_action = "jump"
        app.input_handler.handle_discrete_events(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)], app,
        )
        assert app.rebinding_action is None
        assert app.prefs.bindings["jump"] == pygame.K_SPACE
        assert app.settings_open is True  # Esc cancelled the listen, did not close Settings

        app.rebinding_action = "jump"
        app.input_handler.handle_discrete_events(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3)], app,
        )
        assert app.rebinding_action == "jump"  # still listening
        assert app.prefs.bindings["jump"] == pygame.K_SPACE
    finally:
        pygame.quit()


def test_reset_keys_restores_defaults(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.set_binding("inventory", pygame.K_u)
        app.reset_bindings()
        assert app.prefs.bindings == DEFAULT_BINDINGS
    finally:
        pygame.quit()


def test_binding_chips_and_reset_stay_inside_the_settings_panel():
    panel = settings_panel_rect()
    for i, (action, _label) in enumerate(BINDABLE_ACTIONS):
        chip = settings_binding_button_rect(i)
        assert panel.contains(chip), action
        assert pause_button_at_screen_pos(chip.center, settings_open=True) == f"bind:{action}"
    reset = settings_reset_bindings_rect()
    back_row = settings_row_rect(0)
    assert panel.contains(reset)
    assert not reset.colliderect(back_row)
    assert pause_button_at_screen_pos(reset.center, settings_open=True) == "reset_bindings"


def test_bound_key_falls_back_without_prefs():
    assert bound_key(None, "inventory") == pygame.K_i
    assert serialize_bindings(DEFAULT_BINDINGS)["inventory"] == "i"
