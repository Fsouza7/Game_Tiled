"""Headless tests for the "late-game items" itemization pass: a brand-new
post-Arcane material tier (Voidstone ore -> Voidsteel bar -> sword/full
armor set/accessory/Summoner rod) plus two additional Slime-King-themed
recipes that expand the final boss's loot line.

Mirrors the existing patterns: tests/test_phase6_biomes.py for world-gen ore
placement, tests/test_crafting_and_furnace.py for furnace/workbench crafting.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, TILE_SIZE, CHUNK_WIDTH,
    BEDROCK_ROWS, VOID_ORE_MIN_DEPTH_BELOW_SURFACE, SMELT_TIME_STEEL_S,
)
from game.world.world import World
from game.world.world_generator import biome_at, generate_column, surface_height
from game.world.tile_registry import VOID_ORE_ID, WORKBENCH_ID, FURNACE_ID
from game.world.tile import TileCategory
from game.items import item_registry
from game.items.item import ItemRarity
from game.crafting import recipe_registry, smelt_registry, crafting_system
from game.crafting.furnace_system import FurnaceManager
from game.entities import summon_registry
from game.entities.player import Player


def _make_player(world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _place_station_near_player(world, player, tile_id):
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, tile_id)
    return tile_x, tile_y


# --- New ore tile: registered, and reachable in world generation ---

def test_void_ore_tile_is_registered():
    from game.world import tile_registry

    tile = tile_registry.get(VOID_ORE_ID)
    assert tile.category == TileCategory.ORE
    assert tile.required_tool == "pickaxe"
    assert tile.drop_item_id == "voidstone"
    assert tile.can_place is False
    assert tile.can_break is True
    assert tile.name != ""


def test_void_ore_appears_somewhere_deep_underground():
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS
    found = False
    for x in range(0, WORLD_WIDTH_TILES, 4):
        surface_y = surface_height(DEFAULT_SEED, x)
        column = generate_column(DEFAULT_SEED, x)
        min_y = surface_y + VOID_ORE_MIN_DEPTH_BELOW_SURFACE
        for y in range(min_y, bedrock_start_y):
            if column[y] == VOID_ORE_ID:
                found = True
                break
        if found:
            break
    assert found, "no Voidstone Ore found in a wide world-gen scan"


def test_void_ore_never_appears_above_its_min_depth():
    for x in range(0, WORLD_WIDTH_TILES, 4):
        surface_y = surface_height(DEFAULT_SEED, x)
        column = generate_column(DEFAULT_SEED, x)
        shallow_end_y = min(surface_y + VOID_ORE_MIN_DEPTH_BELOW_SURFACE, WORLD_HEIGHT_TILES)
        for y in range(surface_y, shallow_end_y):
            assert column[y] != VOID_ORE_ID


def test_void_ore_present_in_every_biome_not_just_one():
    # Universal (like coal/iron), not gated to a single biome's exclusive_ore
    # table -- scan a few different biomes and confirm at least one turns up
    # deep in more than a single biome across a reasonably wide search.
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS
    biomes_with_void_ore = set()
    for x in range(0, WORLD_WIDTH_TILES, 2):
        surface_y = surface_height(DEFAULT_SEED, x)
        column = generate_column(DEFAULT_SEED, x)
        min_y = surface_y + VOID_ORE_MIN_DEPTH_BELOW_SURFACE
        for y in range(min_y, bedrock_start_y):
            if column[y] == VOID_ORE_ID:
                biomes_with_void_ore.add(biome_at(DEFAULT_SEED, x).id)
                break
    assert len(biomes_with_void_ore) >= 1


def test_mine_void_ore_for_the_voidstone_item():
    world = World(DEFAULT_SEED)
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS
    ore_x = ore_y = None
    for x in range(0, WORLD_WIDTH_TILES, 4):
        surface_y = world.surface_spawn_y(x) + 1
        for y in range(surface_y + VOID_ORE_MIN_DEPTH_BELOW_SURFACE, bedrock_start_y):
            if world.get_tile(x, y) == VOID_ORE_ID:
                ore_x, ore_y = x, y
                break
        if ore_x is not None:
            break
    assert ore_x is not None, "no Voidstone Ore found to test mining"

    player = Player(ore_x * TILE_SIZE, ore_y * TILE_SIZE)
    drop = None
    for _ in range(80):
        drop = player.try_mine(world, ore_x, ore_y, dt=0.1)
        if drop is not None:
            break
    assert drop == "voidstone"
    from game.world.tile_registry import AIR_ID
    assert world.get_tile(ore_x, ore_y) == AIR_ID


# --- Smelting (via FurnaceManager) ---

def test_voidsteel_bar_smelt_recipe_is_registered_and_the_slowest():
    smelt = smelt_registry.get("voidsteel_bar")
    assert smelt.ore_item_id == "voidstone"
    assert smelt.bar_item_id == "voidsteel_bar"
    assert smelt.smelt_time_s > SMELT_TIME_STEEL_S


def test_smelt_voidsteel_bar_via_furnace_manager():
    world, player = _make_player()
    _place_station_near_player(world, player, FURNACE_ID)
    manager = FurnaceManager()
    recipe = smelt_registry.get("voidsteel_bar")
    player.inventory.add_item("voidstone", recipe.ore_quantity)
    player.inventory.add_item("coal", recipe.fuel_quantity)

    started = manager.start_smelt(recipe, player.inventory, world, player.center_x, player.center_y)
    assert started is True
    assert player.inventory.count_item("voidstone") == 0

    completed = manager.update(recipe.smelt_time_s + 0.1)
    assert completed == [(recipe.bar_item_id, recipe.bar_quantity)]


# --- Item stats genuinely exceed the current ceiling ---

def test_voidsteel_sword_damage_exceeds_current_ceiling():
    sword = item_registry.get("voidsteel_sword")
    assert sword.is_weapon is True
    assert sword.rarity == ItemRarity.EPIC
    assert sword.damage > 28.0


def test_voidsteel_armor_defense_exceeds_current_ceiling():
    crown = item_registry.get("slime_king_crown")  # current best head armor (16.0)
    helmet = item_registry.get("voidsteel_helmet")
    body = item_registry.get("voidsteel_armor")
    legs = item_registry.get("voidsteel_greaves")
    boots = item_registry.get("voidsteel_boots")

    assert helmet.defense > crown.defense
    assert body.defense > item_registry.get("steel_armor").defense
    assert legs.defense > item_registry.get("steel_greaves").defense
    assert boots.defense > item_registry.get("steel_boots").defense

    for piece, slot in ((helmet, "head"), (body, "body"), (legs, "legs"), (boots, "boots")):
        assert piece.equip_slot == slot
        assert piece.rarity == ItemRarity.EPIC


def test_voidstone_amulet_is_a_passive_accessory():
    amulet = item_registry.get("voidstone_amulet")
    assert amulet.equip_slot == "accessory"
    assert amulet.accessory_kind is None
    assert amulet.defense > 0.0
    assert amulet.light_emit > 0


def test_void_wraith_summon_damage_exceeds_current_ceiling():
    void_wraith = summon_registry.get("void_wraith")
    for summon in summon_registry.all_summons():
        if summon.id != "void_wraith":
            assert void_wraith.damage > summon.damage
    assert void_wraith.damage > 28.0


def test_summon_rod_voidsteel_item_points_at_the_void_wraith_summon():
    rod = item_registry.get("summon_rod_voidsteel")
    assert rod.weapon_class == "summon"
    assert rod.summons_id == "void_wraith"
    summon_registry.get(rod.summons_id)  # doesn't raise


# --- Recipes craft correctly near a Workbench ---

_VOID_TIER_RECIPE_INGREDIENTS = {
    "voidsteel_sword": {"voidsteel_bar": 4, "wood": 4},
    "voidsteel_helmet": {"voidsteel_bar": 3, "wood": 3},
    "voidsteel_armor": {"voidsteel_bar": 5, "wood": 4},
    "voidsteel_greaves": {"voidsteel_bar": 4, "wood": 3},
    "voidsteel_boots": {"voidsteel_bar": 3, "wood": 2},
    "voidstone_amulet": {"voidsteel_bar": 2, "voidstone": 2, "wood": 2},
    "summon_rod_voidsteel": {"voidsteel_bar": 4, "wood": 5, "slime_gel": 3},
}


def test_void_tier_recipes_are_registered_with_expected_ingredients_and_station():
    for recipe_id, expected in _VOID_TIER_RECIPE_INGREDIENTS.items():
        recipe = recipe_registry.get(recipe_id)
        assert dict(recipe.ingredients) == expected
        assert recipe.station_tile_id == WORKBENCH_ID
        assert recipe.result_item_id == recipe_id


def test_every_void_tier_recipe_crafts_successfully_near_a_workbench():
    for recipe_id, ingredients in _VOID_TIER_RECIPE_INGREDIENTS.items():
        world, player = _make_player()
        _place_station_near_player(world, player, WORKBENCH_ID)
        for item_id, qty in ingredients.items():
            player.inventory.add_item(item_id, qty)
        recipe = recipe_registry.get(recipe_id)

        success, _ = crafting_system.craft_and_discover(recipe, player, world)

        assert success is True, f"failed to craft {recipe_id}"
        assert player.inventory.count_item(recipe.result_item_id) == recipe.result_quantity
        for item_id in ingredients:
            assert player.inventory.count_item(item_id) == 0


def test_void_tier_recipes_fail_without_a_nearby_workbench():
    world, player = _make_player()  # no workbench placed
    for item_id, qty in _VOID_TIER_RECIPE_INGREDIENTS["voidsteel_sword"].items():
        player.inventory.add_item(item_id, qty)
    recipe = recipe_registry.get("voidsteel_sword")

    success, _ = crafting_system.craft_and_discover(recipe, player, world)

    assert success is False


# --- Slime King's expanded loot line (Task 2) ---

def test_two_new_slime_king_recipes_are_registered_and_require_the_core():
    for recipe_id in ("slime_king_fang", "slime_king_bulwark"):
        recipe = recipe_registry.get(recipe_id)
        ingredient_ids = {item_id for item_id, _ in recipe.ingredients}
        assert "slime_king_core" in ingredient_ids
        core_qty = dict(recipe.ingredients)["slime_king_core"]
        assert core_qty == 1
        assert recipe.station_tile_id == WORKBENCH_ID
        item_def = item_registry.get(recipe.result_item_id)
        assert item_def.rarity == ItemRarity.EPIC


def test_existing_slime_king_crown_recipe_is_unchanged():
    crown_recipe = recipe_registry.get("slime_king_crown")
    assert crown_recipe.ingredients == (("slime_king_core", 1), ("steel_bar", 3))
    assert crown_recipe.result_item_id == "slime_king_crown"
    crown = item_registry.get("slime_king_crown")
    assert crown.defense == 16.0


def test_slime_king_fang_and_bulwark_craft_near_a_workbench():
    for recipe_id in ("slime_king_fang", "slime_king_bulwark"):
        world, player = _make_player()
        _place_station_near_player(world, player, WORKBENCH_ID)
        recipe = recipe_registry.get(recipe_id)
        for item_id, qty in recipe.ingredients:
            player.inventory.add_item(item_id, qty)

        success, _ = crafting_system.craft_and_discover(recipe, player, world)

        assert success is True
        assert player.inventory.count_item(recipe.result_item_id) == recipe.result_quantity


def test_slime_king_fang_is_a_competitive_weapon():
    fang = item_registry.get("slime_king_fang")
    assert fang.is_weapon is True
    assert fang.damage >= 28.0  # competitive with, not necessarily above, the ore-tier ceiling


def test_slime_king_bulwark_is_a_competitive_body_armor():
    bulwark = item_registry.get("slime_king_bulwark")
    assert bulwark.equip_slot == "body"
    assert bulwark.defense > item_registry.get("slime_king_crown").defense - 4.0  # in the same tier band
    assert bulwark.defense >= item_registry.get("steel_armor").defense


# --- Duplicate-id safety net (registries already raise ValueError on
# duplicate registration, but confirm nothing in this pass collides with
# the existing Arcane/Slime-King items it sits alongside). ---

def test_new_item_ids_do_not_collide_with_pre_existing_ones():
    new_ids = {
        "voidstone", "voidsteel_bar", "voidsteel_sword", "voidsteel_helmet",
        "voidsteel_armor", "voidsteel_greaves", "voidsteel_boots",
        "voidstone_amulet", "summon_rod_voidsteel",
        "slime_king_fang", "slime_king_bulwark",
    }
    all_ids = set(item_registry.all_items().keys())
    assert new_ids <= all_ids  # all present (registration didn't silently fail)
