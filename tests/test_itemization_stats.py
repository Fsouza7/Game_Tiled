"""Headless tests for the item-stat engine (crit_chance/crit_damage_mult/
move_speed_bonus) added on top of the existing item schema, plus the new
Arcane-tier gear (body/greaves/boots/sword/rod/accessories) that
demonstrates it. Mirrors the style of test_equipment.py/test_phase4_combat.py
-- new file only, no existing test file touched.
"""
import dataclasses

import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, PLAYER_MOVE_SPEED
from game.entities.player import Player
from game.entities.enemy import Enemy
from game.entities.summon import Summon
from game.entities import enemy_registry, summon_registry
from game.combat import combat_system
from game.crafting import recipe_registry, crafting_system
from game.items import item_registry
from game.world.world import World
from game.world.tile_registry import WORKBENCH_ID, AIR_ID


def _make_player_at(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    return Player(x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


def _find_clear_air_column(world: World, near_x: int, search_radius: int = 40) -> int:
    for offset in range(search_radius):
        for x in (near_x + offset, near_x - offset):
            if 0 <= x < WORLD_WIDTH_TILES:
                surface_y = world.surface_spawn_y(x) + 1
                if world.get_tile(x, surface_y - 1) == AIR_ID:
                    return x
    raise AssertionError("no clear surface column found near_x for placing a workbench")


# --- ItemDef schema ---

def test_new_stat_fields_exist_with_documented_defaults():
    item_def = item_registry.get("wood_sword")  # any item -- defaults apply
    assert item_def.crit_chance == 0.0
    assert item_def.crit_damage_mult == 1.5
    assert item_def.move_speed_bonus == 0.0


# --- combat: melee crit ---

def test_zero_crit_chance_never_crits_over_many_trials():
    # A fresh Player+Enemy pair per trial: _try_melee_attack grants Attack
    # XP on a successful hit, so reusing one player across trials would let
    # its attack_damage_multiplier drift upward mid-loop and break the
    # exact-equality check below for reasons unrelated to crit at all.
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    base_item = item_registry.get("wood_sword")
    assert base_item.crit_chance == 0.0

    for _ in range(200):
        player = _make_player_at(world, x)
        enemy = Enemy(enemy_registry.get("slime_king"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
        combat_system._try_melee_attack(player, base_item, [enemy], 1.0, 0.0)
        damage_dealt = enemy.enemy_def.max_health - enemy.health
        assert damage_dealt == base_item.damage  # never scaled by crit_damage_mult


def test_full_crit_chance_always_deals_crit_scaled_melee_damage():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    crit_item = dataclasses.replace(
        item_registry.get("wood_sword"), crit_chance=1.0, crit_damage_mult=2.0,
    )

    for _ in range(50):
        player = _make_player_at(world, x)  # fresh player per trial, see above
        enemy = Enemy(enemy_registry.get("slime_king"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
        combat_system._try_melee_attack(player, crit_item, [enemy], 1.0, 0.0)
        damage_dealt = enemy.enemy_def.max_health - enemy.health
        assert damage_dealt == crit_item.damage * 2.0


# --- combat: ranged crit (respects Attack vs Magic multiplier) ---

def test_full_crit_chance_always_deals_crit_scaled_ranged_damage():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    crit_bow = dataclasses.replace(
        item_registry.get("wood_bow"), crit_chance=1.0, crit_damage_mult=1.75, ammo_item_id=None,
    )
    projectile = combat_system._try_ranged_attack(player, crit_bow, 1.0, 0.0)
    assert projectile is not None
    assert projectile.damage == crit_bow.damage * player.skills.attack_damage_multiplier() * 1.75


def test_full_crit_chance_applies_after_magic_multiplier_on_magic_weapons():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    crit_staff = dataclasses.replace(
        item_registry.get("arcane_staff"), crit_chance=1.0, crit_damage_mult=2.0,
    )
    projectile = combat_system._try_ranged_attack(player, crit_staff, 1.0, 0.0)
    assert projectile is not None
    assert projectile.uses_magic is True
    assert projectile.damage == crit_staff.damage * player.skills.magic_damage_multiplier() * 2.0


# --- combat: summon rod crit stretch goal ---

def test_summon_rod_crit_scales_summon_damage_when_rod_is_selected():
    """The optional stretch goal: resolve_summon_attacks reads crit off the
    currently-selected rod's ItemDef. Verified by swapping the registered
    summon_rod_arcane entry for a guaranteed-crit copy for the duration of
    the test (restored in `finally`), since resolve_summon_attacks looks the
    rod up by id through item_registry, not by a passed-in ItemDef."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    player.inventory.add_item("summon_rod_arcane", 1)
    player.inventory.select_hotbar(1)

    original_rod = item_registry.get("summon_rod_arcane")
    crit_rod = dataclasses.replace(original_rod, crit_chance=1.0, crit_damage_mult=2.0)
    item_registry._ITEMS["summon_rod_arcane"] = crit_rod
    try:
        summon_def = summon_registry.get("arcane_familiar")
        summon = Summon(summon_def, player.center_x, player.center_y)
        summon.attack_cooldown_remaining = 0.0
        enemy = Enemy(enemy_registry.get("slime_king"), player.center_x, player.center_y)

        # Captured before the hit -- resolve_summon_attacks grants Magic XP
        # for this same hit, so reading the multiplier afterward would
        # reflect a level-up this very hit just caused, not what applied
        # to the hit itself.
        pre_hit_multiplier = player.skills.magic_damage_multiplier()
        combat_system.resolve_summon_attacks(player, [summon], [enemy])

        expected = summon.damage * pre_hit_multiplier * 2.0
        damage_dealt = enemy.enemy_def.max_health - enemy.health
        assert damage_dealt == expected
    finally:
        item_registry._ITEMS["summon_rod_arcane"] = original_rod


# --- move speed bonus ---

def test_total_move_speed_bonus_sums_across_equipped_slots():
    player = Player(0, 0)
    assert player.equipment.total_move_speed_bonus() == 0.0

    # Verify real summation (not just a single-slot passthrough) by putting
    # a move-speed item in two different slots at once.
    player.equipment.slots["accessory"] = "swift_anklet"
    player.equipment.slots["head"] = "swift_anklet"
    expected = item_registry.get("swift_anklet").move_speed_bonus * 2
    assert player.equipment.total_move_speed_bonus() == expected
    assert expected > 0.0


def test_player_with_move_speed_accessory_moves_faster():
    plain_player = Player(0, 0)
    plain_player.move_right()
    plain_speed = plain_player.x_vel

    boosted_player = Player(0, 0)
    # A fresh Player starts with a Grapple Hook already in the accessory
    # slot (see Player.__init__) -- free it up first.
    assert boosted_player.equipment.unequip_to_inventory(boosted_player.inventory, "accessory")
    boosted_player.inventory.add_item("swift_anklet", 1)
    assert boosted_player.equipment.equip_from_inventory(boosted_player.inventory, "swift_anklet")
    boosted_player.move_right()
    boosted_speed = boosted_player.x_vel

    assert boosted_speed > plain_speed
    assert plain_speed == PLAYER_MOVE_SPEED

    boosted_player.move_left()
    assert boosted_player.x_vel == -(PLAYER_MOVE_SPEED + item_registry.get("swift_anklet").move_speed_bonus)


# --- tooltip lines ---

def test_tooltip_shows_crit_and_move_speed_lines_when_present():
    from game.rendering.renderer import Renderer

    renderer = Renderer.__new__(Renderer)
    sword_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("arcane_sword")))
    assert any(k.startswith("Crit Chance") for k in sword_lines)

    anklet_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("swift_anklet")))
    assert any(k.startswith("Move Speed") for k in anklet_lines)

    # A weapon with no crit_chance shouldn't show the line at all.
    plain_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("wood_sword")))
    assert not any(k.startswith("Crit Chance") for k in plain_lines)


# --- Arcane tier: registration + stats ---

def test_arcane_armor_pieces_are_registered_and_beat_steel():
    body = item_registry.get("arcane_body")
    greaves = item_registry.get("arcane_greaves")
    boots = item_registry.get("arcane_boots")

    assert body.equip_slot == "body" and body.category.value == "armor"
    assert greaves.equip_slot == "legs" and greaves.category.value == "armor"
    assert boots.equip_slot == "boots" and boots.category.value == "armor"

    assert body.defense > item_registry.get("steel_armor").defense
    assert greaves.defense > item_registry.get("steel_greaves").defense
    assert boots.defense > item_registry.get("steel_boots").defense

    from game.items.item import ItemRarity
    for item_def in (body, greaves, boots):
        assert item_def.rarity == ItemRarity.EPIC  # never a 5th rarity value


def test_arcane_sword_is_registered_with_crit_and_beats_wood_sword_damage():
    sword = item_registry.get("arcane_sword")
    assert sword.is_weapon and not sword.is_ranged
    assert sword.damage > item_registry.get("wood_sword").damage
    assert sword.damage > 20.0  # above the steel tier this pass targets
    assert sword.crit_chance > 0.0
    assert sword.crit_damage_mult > 1.0


def test_arcane_staff_also_has_crit_fields_set():
    staff = item_registry.get("arcane_staff")
    assert staff.uses_magic is True
    assert staff.crit_chance > 0.0
    assert staff.crit_damage_mult > 1.0


def test_arcane_summon_rod_and_summon_def_are_registered_above_iron_tier():
    rod = item_registry.get("summon_rod_arcane")
    assert rod.is_weapon and rod.weapon_class == "summon"
    summon_def = summon_registry.get(rod.summons_id)
    assert summon_def.id == "arcane_familiar"
    assert summon_def.damage > summon_registry.get("iron_guardian").damage
    assert summon_def.damage > 20.0


def test_move_speed_accessories_are_registered_with_sane_bonuses():
    swift = item_registry.get("swift_anklet")
    arcane = item_registry.get("arcane_anklet")
    assert swift.equip_slot == "accessory"
    assert arcane.equip_slot == "accessory"
    assert swift.accessory_kind is None  # passive stat stick, not E-triggered
    assert arcane.accessory_kind is None
    assert 0.0 < swift.move_speed_bonus < PLAYER_MOVE_SPEED
    assert 0.0 < arcane.move_speed_bonus < PLAYER_MOVE_SPEED
    assert arcane.move_speed_bonus > swift.move_speed_bonus


# --- Arcane tier: recipes craft correctly near a Workbench ---

def _craft_near_workbench(item_id, ingredients):
    world = World(DEFAULT_SEED)
    x = _find_clear_air_column(world, WORLD_WIDTH_TILES // 2)
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    for ingredient_id, qty in ingredients:
        player.inventory.add_item(ingredient_id, qty)

    recipe = recipe_registry.get(item_id)
    assert recipe.station_tile_id == WORKBENCH_ID
    # Away from any workbench: ingredients present, station missing.
    assert crafting_system.has_ingredients(recipe, player.inventory)
    assert not crafting_system.can_craft(recipe, player.inventory, world, player.center_x, player.center_y)

    assert world.try_place_tile(x, surface_y - 1, WORKBENCH_ID)
    assert crafting_system.can_craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert crafting_system.craft(recipe, player.inventory, world, player.center_x, player.center_y)
    assert player.inventory.count_item(item_id) == 1
    for ingredient_id, qty in ingredients:
        assert player.inventory.count_item(ingredient_id) == 0


def test_arcane_body_recipe_crafts_near_workbench():
    _craft_near_workbench("arcane_body", (("arcane_bar", 4), ("wood", 4)))


def test_arcane_greaves_recipe_crafts_near_workbench():
    _craft_near_workbench("arcane_greaves", (("arcane_bar", 3), ("wood", 3)))


def test_arcane_boots_recipe_crafts_near_workbench():
    _craft_near_workbench("arcane_boots", (("arcane_bar", 2), ("wood", 2)))


def test_arcane_sword_recipe_crafts_near_workbench():
    _craft_near_workbench("arcane_sword", (("arcane_bar", 3), ("wood", 3)))


def test_summon_rod_arcane_recipe_crafts_near_workbench():
    _craft_near_workbench("summon_rod_arcane", (("arcane_bar", 3), ("wood", 5)))


def test_swift_anklet_recipe_crafts_near_workbench():
    _craft_near_workbench("swift_anklet", (("steel_bar", 2), ("feather", 4)))


def test_arcane_anklet_recipe_crafts_near_workbench():
    _craft_near_workbench("arcane_anklet", (("arcane_bar", 2), ("feather", 6)))


def test_all_new_recipes_reference_real_items_with_positive_quantities():
    for recipe_id in (
        "arcane_body", "arcane_greaves", "arcane_boots", "arcane_sword",
        "summon_rod_arcane", "swift_anklet", "arcane_anklet",
    ):
        recipe = recipe_registry.get(recipe_id)
        item_registry.get(recipe.result_item_id)
        for item_id, qty in recipe.ingredients:
            item_registry.get(item_id)
            assert qty > 0
