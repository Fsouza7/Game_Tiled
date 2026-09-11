"""Headless tests for the Phase 6 biome-exclusive mobs: Frost Hopper (Snow)
and Swamp Mosquito (Jungle). Registry gating, animation tables, drops,
recipes, and the F9 debug spawn roster.
"""
import os

import pygame  # noqa: F401

from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT
from game.world.biome_registry import FOREST_ID, DESERT_ID, SNOW_ID, JUNGLE_ID
from game.entities.enemy_def import AIType, SpawnTime
from game.entities.enemy_registry import get as get_enemy_def
from game.entities import enemy_registry
from game.entities.enemy_spawner import EnemySpawner
from game.items import item_registry
from game.items.item import ItemCategory, ItemRarity
from game.crafting import recipe_registry
from game.world.tile_registry import WORKBENCH_ID
from game.rendering import assets


# --- registry biome gating (both ways, mirroring scorpion in test_phase6_biomes) ---

def test_frost_hopper_is_snow_only():
    hopper = get_enemy_def("frost_hopper")
    assert hopper.biome_id == SNOW_ID
    assert hopper.ai_type == AIType.HOP
    assert hopper.spawn_time == SpawnTime.ANY
    assert hopper.drop_item_id == "frost_shard"


def test_swamp_mosquito_is_jungle_only():
    mosquito = get_enemy_def("swamp_mosquito")
    assert mosquito.biome_id == JUNGLE_ID
    assert mosquito.ai_type == AIType.FLY
    assert mosquito.spawn_time == SpawnTime.ANY
    assert mosquito.drop_item_id == "mosquito_wing"


def test_spawner_never_picks_frost_hopper_outside_snow():
    spawner = EnemySpawner()
    for biome_id in (FOREST_ID, DESERT_ID, JUNGLE_ID):
        for _ in range(200):
            picked = spawner._pick_weighted_enemy(is_night=False, biome_id=biome_id)
            assert picked.id != "frost_hopper"


def test_spawner_can_pick_frost_hopper_in_snow():
    spawner = EnemySpawner()
    picks = {spawner._pick_weighted_enemy(is_night=False, biome_id=SNOW_ID).id for _ in range(300)}
    assert "frost_hopper" in picks


def test_spawner_never_picks_swamp_mosquito_outside_jungle():
    spawner = EnemySpawner()
    for biome_id in (FOREST_ID, DESERT_ID, SNOW_ID):
        for _ in range(200):
            picked = spawner._pick_weighted_enemy(is_night=False, biome_id=biome_id)
            assert picked.id != "swamp_mosquito"


def test_spawner_can_pick_swamp_mosquito_in_jungle():
    spawner = EnemySpawner()
    picks = {spawner._pick_weighted_enemy(is_night=False, biome_id=JUNGLE_ID).id for _ in range(300)}
    assert "swamp_mosquito" in picks


def test_spawner_default_biome_excludes_both_exclusives():
    spawner = EnemySpawner()
    for _ in range(200):
        picked = spawner._pick_weighted_enemy(is_night=False)
        assert picked.id not in ("frost_hopper", "swamp_mosquito")


def test_snow_and_jungle_exclusives_do_not_cross_biomes():
    # Both-ways: a Snow pick must never be the Jungle mosquito, and a Jungle
    # pick must never be the Frost Hopper (the positive "can pick" tests
    # above don't prove the other exclusive is gated out).
    spawner = EnemySpawner()
    snow_picks = {spawner._pick_weighted_enemy(is_night=False, biome_id=SNOW_ID).id for _ in range(300)}
    jungle_picks = {spawner._pick_weighted_enemy(is_night=False, biome_id=JUNGLE_ID).id for _ in range(300)}
    assert "swamp_mosquito" not in snow_picks
    assert "frost_hopper" not in jungle_picks


# --- animation tables ---

def _assert_idle_chase_hit_both_facings(table):
    for state in ("idle", "chase", "hit"):
        for facing in ("left", "right"):
            frames = table[(state, facing)]
            assert len(frames) >= 1
            assert frames[0].get_width() > 0


def test_frost_hopper_and_swamp_mosquito_animation_tables():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    assert os.path.isfile(assets.SLIME_IDLE_PATH)
    assert os.path.isfile(assets.MOSQUITO_PATH)

    hopper = assets.load_frost_hopper_animations(assets.FROST_HOPPER_SPRITE_SIZE)
    mosquito = assets.load_swamp_mosquito_animations(assets.SWAMP_MOSQUITO_SPRITE_SIZE)
    _assert_idle_chase_hit_both_facings(hopper)
    _assert_idle_chase_hit_both_facings(mosquito)

    tables = assets.load_enemy_animations()
    assert "frost_hopper" in tables
    assert "swamp_mosquito" in tables
    _assert_idle_chase_hit_both_facings(tables["frost_hopper"])
    _assert_idle_chase_hit_both_facings(tables["swamp_mosquito"])


# --- drops + recipes ---

def test_exclusive_drop_items_exist():
    shard = item_registry.get("frost_shard")
    assert shard.category == ItemCategory.MATERIAL
    assert shard.rarity == ItemRarity.UNCOMMON
    assert shard.icon_key == "frost_shard"

    wing = item_registry.get("mosquito_wing")
    assert wing.category == ItemCategory.MATERIAL
    assert wing.rarity == ItemRarity.COMMON
    assert wing.icon_key == "mosquito_wing"

    charm = item_registry.get("wing_charm")
    assert charm.equip_slot == "accessory"
    assert charm.light_emit == 4


def test_exclusive_drop_recipes_exist():
    arrows = recipe_registry.get("frost_arrows")
    assert arrows.result_item_id == "arrow"
    assert arrows.result_quantity == 8
    assert arrows.ingredients == (("frost_shard", 1), ("wood", 1))
    assert arrows.station_tile_id is None

    charm = recipe_registry.get("wing_charm")
    assert charm.result_item_id == "wing_charm"
    assert charm.ingredients == (("mosquito_wing", 4), ("slime_gel", 2))
    assert charm.station_tile_id == WORKBENCH_ID


# --- debug spawn roster ---

def test_debug_spawn_all_enemies_includes_the_new_mobs():
    from game.core.game_app import GameApp
    from game.settings import DEFAULT_SEED
    from game.entities.enemy import Enemy
    from game.entities.boss import Boss

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.debug_spawn_all_enemies()
        spawned = {e.enemy_def.id for e in app.enemies if isinstance(e, Enemy) and not isinstance(e, Boss)}
        assert {"frost_hopper", "swamp_mosquito"} <= spawned
    finally:
        pygame.quit()
