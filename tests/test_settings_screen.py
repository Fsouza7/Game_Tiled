"""Headless tests for the improved Settings screen: persisted audio
preferences (game/core/settings_store.py), GameApp's volume-adjustment
methods, and the pause menu's Settings sub-panel (layout + real click
path through InputHandler).
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, VOLUME_STEP
from game.core import settings_store
from game.core import sfx
from game.rendering.renderer import (
    pause_menu_button_rects, pause_button_at_screen_pos, settings_panel_rect, settings_row_rect,
)


# --- settings_store: load/save ---

def test_load_returns_defaults_when_no_file_exists(tmp_path):
    prefs = settings_store.load(str(tmp_path / "does_not_exist.json"))
    assert prefs.music_volume == settings_store.MUSIC_VOLUME
    assert prefs.sfx_volume == settings_store.SFX_VOLUME


def test_save_then_load_round_trips_values(tmp_path):
    path = str(tmp_path / "settings.json")
    original = settings_store.Settings(music_volume=0.2, sfx_volume=0.9)
    settings_store.save(original, path)

    loaded = settings_store.load(path)
    assert loaded.music_volume == 0.2
    assert loaded.sfx_volume == 0.9


def test_load_clamps_out_of_range_values_from_a_hand_edited_file(tmp_path):
    import json

    path = str(tmp_path / "settings.json")
    with open(path, "w") as f:
        json.dump({"music_volume": 5.0, "sfx_volume": -3.0}, f)

    prefs = settings_store.load(path)
    assert prefs.music_volume == 1.0
    assert prefs.sfx_volume == 0.0


def test_load_degrades_to_defaults_on_a_corrupt_file(tmp_path):
    path = str(tmp_path / "settings.json")
    with open(path, "w") as f:
        f.write("not valid json {{{")

    prefs = settings_store.load(path)  # must not raise
    assert prefs.music_volume == settings_store.MUSIC_VOLUME
    assert prefs.sfx_volume == settings_store.SFX_VOLUME


def test_save_creates_the_saves_directory_if_missing(tmp_path):
    path = str(tmp_path / "nested" / "settings.json")
    settings_store.save(settings_store.Settings(0.1, 0.2), path)
    assert settings_store.load(path).music_volume == 0.1


# --- GameApp: adjust_music_volume / adjust_sfx_volume ---

def test_adjust_music_volume_clamps_applies_and_persists(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.prefs.music_volume = 0.95
        app.adjust_music_volume(VOLUME_STEP)
        assert app.prefs.music_volume == 1.0  # clamped, not 1.05
        assert pygame.mixer.music.get_volume() == 1.0

        app.adjust_music_volume(-10.0)
        assert app.prefs.music_volume == 0.0
        assert pygame.mixer.music.get_volume() == 0.0

        reloaded = settings_store.load(str(tmp_path / "settings.json"))
        assert reloaded.music_volume == 0.0  # the last adjustment was persisted
    finally:
        pygame.quit()


def test_adjust_sfx_volume_clamps_applies_and_persists(tmp_path, monkeypatch):
    from game.core.game_app import GameApp

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.prefs.sfx_volume = 0.05
        app.adjust_sfx_volume(-VOLUME_STEP)
        assert app.prefs.sfx_volume == 0.0
        assert sfx._volume == 0.0

        app.adjust_sfx_volume(10.0)
        assert app.prefs.sfx_volume == 1.0
        assert sfx._volume == 1.0

        reloaded = settings_store.load(str(tmp_path / "settings.json"))
        assert reloaded.sfx_volume == 1.0
    finally:
        sfx.set_volume(1.0)
        pygame.quit()


def test_game_app_boot_loads_and_applies_persisted_prefs(tmp_path, monkeypatch):
    """The whole chain end to end: a settings.json written before boot is
    picked up by GameApp.__init__ and actually applied to the live mixer,
    not just stored on self.prefs."""
    from game.core.game_app import GameApp

    path = str(tmp_path / "settings.json")
    settings_store.save(settings_store.Settings(music_volume=0.25, sfx_volume=0.55), path)
    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", path)

    app = GameApp(seed=DEFAULT_SEED)
    try:
        assert app.prefs.music_volume == 0.25
        assert app.prefs.sfx_volume == 0.55
        assert abs(pygame.mixer.music.get_volume() - 0.25) < 1e-6
        assert sfx._volume == 0.55
    finally:
        sfx.set_volume(1.0)
        pygame.quit()


def test_restart_and_load_game_do_not_reset_prefs(tmp_path, monkeypatch):
    """Preferences are not part of "one playthrough" -- Restart/Load must
    leave whatever volume the player set alone (see settings_store.py's
    module docstring)."""
    from game.core.game_app import GameApp
    from game.core import save_system

    monkeypatch.setattr(settings_store, "SETTINGS_FILE_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "save.json"))
    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.adjust_music_volume(-0.15)
        expected = app.prefs.music_volume

        app.restart()
        assert app.prefs.music_volume == expected

        app.save_game()
        app.adjust_music_volume(0.15)
        expected_after_further_adjustment = app.prefs.music_volume
        app.load_game()
        # load_game() rebuilds world/player state from the save file, which
        # never included prefs -- the volume set right before this call
        # must still be exactly what it was, not reverted to whatever was
        # true at save time (or to any default).
        assert app.prefs.music_volume == expected_after_further_adjustment
    finally:
        pygame.quit()


# --- Settings sub-panel: layout + real click path ---

def test_settings_row_rects_do_not_overlap_and_stay_inside_the_panel():
    panel = settings_panel_rect()
    rows = [settings_row_rect(i) for i in range(3)]
    for row in rows:
        assert panel.contains(row)
    for a, b in zip(rows, rows[1:]):
        assert not a.colliderect(b)


def test_settings_button_rects_cover_every_expected_action():
    rects = pause_menu_button_rects(settings_open=True)
    assert set(rects) == {
        "zoom_up", "zoom_down", "music_up", "music_down", "sfx_up", "sfx_down", "back",
    }


def test_settings_panel_click_path_adjusts_zoom_and_volume_through_input_handler():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.paused = True
        app.settings_open = True

        starting_zoom = app.camera.zoom
        zoom_in_rect = pause_menu_button_rects(settings_open=True)["zoom_up"]
        app.input_handler._handle_pause_click(zoom_in_rect.center, app)
        assert app.camera.zoom > starting_zoom

        starting_music = app.prefs.music_volume
        music_down_rect = pause_menu_button_rects(settings_open=True)["music_down"]
        app.input_handler._handle_pause_click(music_down_rect.center, app)
        assert app.prefs.music_volume == max(0.0, starting_music - VOLUME_STEP)

        starting_sfx = app.prefs.sfx_volume
        sfx_up_rect = pause_menu_button_rects(settings_open=True)["sfx_up"]
        app.input_handler._handle_pause_click(sfx_up_rect.center, app)
        assert app.prefs.sfx_volume == min(1.0, starting_sfx + VOLUME_STEP)

        back_rect = pause_menu_button_rects(settings_open=True)["back"]
        app.input_handler._handle_pause_click(back_rect.center, app)
        assert app.settings_open is False
    finally:
        pygame.quit()


def test_pause_button_at_screen_pos_resolves_settings_actions():
    rects = pause_menu_button_rects(settings_open=True)
    for action, rect in rects.items():
        assert pause_button_at_screen_pos(rect.center, settings_open=True) == action


def test_game_app_draws_the_settings_panel_without_crashing():
    """A real draw() pass through _draw_pause_overlay -> _draw_settings_panel
    with the real Renderer, not just the layout math above."""
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.paused = True
        app.settings_open = True
        app.step(dt=1 / 60)  # must not raise
    finally:
        pygame.quit()
