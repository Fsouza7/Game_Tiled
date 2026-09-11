"""Headless tests for the Iron/Steel weapon-tier itemization pass: new
Iron/Steel Sword and Bow items, the Steel-tier Summoner rod + SummonDef
(steel_colossus), and two new passive ACCESSORY items (Warrior's Charm,
Summoner's Trinket). Mirrors the style of tests/test_crafting_and_furnace.py
(_make_player/_place_furnace_near_player) and tests/test_summoner_class.py
(class gating through combat_system.try_attack).
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH
from game.entities.player import Player
from game.entities.summon import Summon
from game.entities import summon_registry
from game.combat import combat_system
from game.crafting import recipe_registry, crafting_system
from game.items import item_registry
from game.items.item import ItemCategory, ItemRarity
from game.world.world import World
from game.world.tile_registry import WORKBENCH_ID


def _make_player(class_id="warrior", world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE, class_id=class_id)
    return world, player


def _place_workbench_near_player(world, player):
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, WORKBENCH_ID)
    return tile_x, tile_y


def _give_ingredients(player, recipe):
    for item_id, qty in recipe.ingredients:
        player.inventory.add_item(item_id, qty)


# --- Iron/Steel Sword: registration + damage progression ---

def test_iron_and_steel_sword_are_registered_melee_weapons():
    for item_id in ("iron_sword", "steel_sword"):
        item_def = item_registry.get(item_id)
        assert item_def.category == ItemCategory.WEAPON
        assert item_def.is_weapon is True
        assert item_def.is_ranged is False
        assert item_def.weapon_class == "normal"
        assert item_def.max_durability is not None and item_def.max_durability > 0


def test_sword_damage_progresses_wood_to_iron_to_steel():
    wood = item_registry.get("wood_sword")
    iron = item_registry.get("iron_sword")
    steel = item_registry.get("steel_sword")
    assert wood.damage < iron.damage < steel.damage


def test_sword_rarity_matches_the_iron_uncommon_steel_rare_convention():
    assert item_registry.get("iron_sword").rarity == ItemRarity.UNCOMMON
    assert item_registry.get("steel_sword").rarity == ItemRarity.RARE


def test_sword_durability_scales_up_by_tier():
    wood = item_registry.get("wood_sword")
    iron = item_registry.get("iron_sword")
    steel = item_registry.get("steel_sword")
    assert wood.max_durability < iron.max_durability < steel.max_durability


# --- Iron/Steel Bow: registration + damage progression ---

def test_iron_and_steel_bow_are_registered_ranged_weapons():
    for item_id in ("iron_bow", "steel_bow"):
        item_def = item_registry.get(item_id)
        assert item_def.category == ItemCategory.WEAPON
        assert item_def.is_weapon is True
        assert item_def.is_ranged is True
        assert item_def.ammo_item_id == "arrow"
        assert item_def.weapon_class == "normal"


def test_bow_damage_progresses_wood_to_iron_to_steel():
    wood = item_registry.get("wood_bow")
    iron = item_registry.get("iron_bow")
    steel = item_registry.get("steel_bow")
    assert wood.damage < iron.damage < steel.damage


# --- Steel-tier Summoner rod + SummonDef ---

def test_steel_colossus_summon_def_is_registered_and_stronger_than_iron_guardian():
    iron_guardian = summon_registry.get("iron_guardian")
    steel_colossus = summon_registry.get("steel_colossus")
    assert steel_colossus.damage > iron_guardian.damage
    assert steel_colossus.id not in ("twig_sprite", "iron_guardian")


def test_summon_rod_steel_item_references_steel_colossus():
    item_def = item_registry.get("summon_rod_steel")
    assert item_def.category == ItemCategory.WEAPON
    assert item_def.is_weapon is True
    assert item_def.is_ranged is False
    assert item_def.weapon_class == "summon"
    assert item_def.summons_id == "steel_colossus"
    summon_registry.get(item_def.summons_id)  # raises if missing


def test_summon_rod_steel_recipe_is_registered():
    recipe = recipe_registry.get("summon_rod_steel")
    assert recipe.result_item_id == "summon_rod_steel"
    assert recipe.station_tile_id == WORKBENCH_ID
    ingredient_ids = {item_id for item_id, _ in recipe.ingredients}
    assert "steel_bar" in ingredient_ids


# --- weapon_class gating: Summoner can cast the new rod, Warrior can't ---

def test_summoner_can_cast_the_steel_rod_and_gets_the_steel_colossus():
    world, player = _make_player("summoner")
    player.inventory.slots[1].item_id = "summon_rod_steel"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    result = combat_system.try_attack(world=world, player=player, enemies=[], aim_world_pos=(player.center_x, player.center_y))
    assert isinstance(result, Summon)
    assert result.summon_def.id == "steel_colossus"


def test_warrior_cannot_cast_the_steel_rod():
    world, player = _make_player("warrior")
    player.inventory.slots[1].item_id = "summon_rod_steel"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    result = combat_system.try_attack(world=world, player=player, enemies=[], aim_world_pos=(player.center_x, player.center_y))
    assert result is None


def test_summoner_cannot_swing_the_new_steel_sword():
    from game.entities.enemy import Enemy
    from game.entities import enemy_registry

    world, player = _make_player("summoner")
    player.inventory.slots[0].item_id = "steel_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    start_health = enemy.health

    result = combat_system.try_attack(world=world, player=player, enemies=[enemy], aim_world_pos=(player.center_x + 1, player.center_y))
    assert result is None
    assert enemy.health == start_health  # blocked -- weapon_class="normal" isn't allowed for Summoner


def test_warrior_can_swing_the_new_iron_sword():
    from game.entities.enemy import Enemy
    from game.entities import enemy_registry

    world, player = _make_player("warrior")
    player.inventory.slots[0].item_id = "iron_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    start_health = enemy.health

    result = combat_system.try_attack(world=world, player=player, enemies=[enemy], aim_world_pos=(player.center_x + 1, player.center_y))
    assert result is None  # melee hits apply directly, nothing returned
    assert enemy.health < start_health


# --- Accessories: passive stat sticks, no accessory_kind ---

def test_new_accessories_are_passive_stat_sticks():
    for item_id in ("warriors_charm", "summoners_trinket"):
        item_def = item_registry.get(item_id)
        assert item_def.category == ItemCategory.ACCESSORY
        assert item_def.equip_slot == "accessory"
        assert item_def.accessory_kind is None  # passive, not an E-triggered active behavior
        assert item_def.defense > 0.0


def test_summoners_trinket_also_emits_light():
    item_def = item_registry.get("summoners_trinket")
    assert item_def.light_emit > 0


def test_equipping_the_warriors_charm_adds_to_total_defense():
    # Player starts with a Grapple Hook already in the accessory slot (see
    # Player.__init__) -- unequip it first so the accessory slot is free.
    _, player = _make_player("warrior")
    assert player.equipment.unequip_to_inventory(player.inventory, "accessory") is True
    before = player.equipment.total_defense()
    assert before == 0.0
    player.inventory.add_item("warriors_charm", 1)
    assert player.equipment.equip_from_inventory(player.inventory, "warriors_charm") is True
    after = player.equipment.total_defense()
    assert after == before + item_registry.get("warriors_charm").defense


def test_equipping_the_summoners_trinket_adds_to_total_light_emit():
    _, player = _make_player("summoner")
    assert player.equipment.unequip_to_inventory(player.inventory, "accessory") is True
    before = player.equipment.total_light_emit()
    assert before == 0
    player.inventory.add_item("summoners_trinket", 1)
    assert player.equipment.equip_from_inventory(player.inventory, "summoners_trinket") is True
    after = player.equipment.total_light_emit()
    assert after == item_registry.get("summoners_trinket").light_emit


# --- Crafting: every new weapon/rod/accessory recipe actually crafts ---

def _assert_recipe_crafts_near_workbench(recipe_id):
    world, player = _make_player()
    _place_workbench_near_player(world, player)
    recipe = recipe_registry.get(recipe_id)
    assert recipe.station_tile_id == WORKBENCH_ID
    _give_ingredients(player, recipe)

    success, _ = crafting_system.craft_and_discover(recipe, player, world)

    assert success is True
    assert player.inventory.count_item(recipe.result_item_id) == recipe.result_quantity


def test_iron_sword_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("iron_sword")


def test_steel_sword_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("steel_sword")


def test_iron_bow_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("iron_bow")


def test_steel_bow_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("steel_bow")


def test_summon_rod_steel_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("summon_rod_steel")


def test_warriors_charm_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("warriors_charm")


def test_summoners_trinket_recipe_crafts_near_a_workbench():
    _assert_recipe_crafts_near_workbench("summoners_trinket")


def test_new_recipes_fail_without_a_nearby_workbench():
    world, player = _make_player()  # no workbench placed
    for recipe_id in ("iron_sword", "steel_sword", "iron_bow", "steel_bow", "summon_rod_steel", "warriors_charm", "summoners_trinket"):
        recipe = recipe_registry.get(recipe_id)
        _give_ingredients(player, recipe)
        assert crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y) is False
