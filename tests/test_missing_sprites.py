"""Headless tests for the missing-sprites pass (Agent C): Crawler, NPC
idle skins, every summon id, and door/bed tile textures. Needs a display
surface for convert_alpha, same as the other asset tests.
"""
import os

import pygame

from game.settings import DEFAULT_SEED, WINDOW_WIDTH, WINDOW_HEIGHT, TILE_SIZE
from game.rendering import assets
from game.world.tile_registry import DOOR_CLOSED_ID, DOOR_OPEN_ID, BED_ID
from game.npcs import npc_registry
from game.entities import character_registry, summon_registry


def _display():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def test_crawler_is_in_load_enemy_animations():
    _display()
    assert os.path.isfile(assets.EYEBALL_PATH)
    anims = assets.load_enemy_animations()
    assert "crawler" in anims
    assert len(anims["crawler"][("idle", "right")]) == 6
    assert len(anims["crawler"][("chase", "right")]) == 4
    assert len(anims["crawler"][("hit", "right")]) == 1
    for state in ("idle", "chase", "hit"):
        frames = anims["crawler"][(state, "right")]
        assert len(frames) >= 1
        opaque = sum(
            1
            for y in range(0, frames[0].get_height(), 4)
            for x in range(0, frames[0].get_width(), 4)
            if frames[0].get_at((x, y))[3] > 0
        )
        assert opaque > 5, f"crawler {state} frame looks empty"


def test_every_summon_id_is_in_load_summon_animations():
    _display()
    anims = assets.load_summon_animations()
    for summon in summon_registry.all_summons():
        assert summon.id in anims, f"no summon animation table for {summon.id}"
        idle = anims[summon.id][("idle", "right")]
        chase = anims[summon.id][("chase", "right")]
        assert len(idle) >= 1
        assert len(chase) >= 1


def test_door_and_bed_ids_are_in_load_tile_textures():
    _display()
    textures = assets.load_tile_textures()
    for tile_id in (DOOR_CLOSED_ID, DOOR_OPEN_ID, BED_ID):
        assert tile_id in textures, f"no tile texture for id {tile_id}"
        surf = textures[tile_id]
        assert surf.get_size() == (TILE_SIZE, TILE_SIZE)
        opaque = sum(
            1
            for y in range(0, surf.get_height(), 4)
            for x in range(0, surf.get_width(), 4)
            if surf.get_at((x, y))[3] > 0
        )
        assert opaque > 5
    closed = pygame.image.tostring(textures[DOOR_CLOSED_ID], "RGBA")
    opened = pygame.image.tostring(textures[DOOR_OPEN_ID], "RGBA")
    assert closed != opened, "open door should not be a copy of the closed door"


def test_npc_defs_have_sprite_character_ids():
    expected = {
        "guide": "mask_dude",
        "merchant": "pink_man",
        "blacksmith": "virtual_guy",
    }
    npcs = {n.id: n for n in npc_registry.all_npcs()}
    assert set(expected) <= set(npcs)
    for npc_id, character_id in expected.items():
        assert npcs[npc_id].sprite_character_id == character_id
        assert character_id != character_registry.DEFAULT_CHARACTER_ID
        character_registry.get(character_id)


def test_game_app_step_with_all_enemies_does_not_crash():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.debug_spawn_all_enemies()
        app.step(dt=1 / 60)
        assert "crawler" in app.renderer.enemy_animations
        for summon in summon_registry.all_summons():
            assert summon.id in app.renderer.summon_animations
    finally:
        pygame.quit()
