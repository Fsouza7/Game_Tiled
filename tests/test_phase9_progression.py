"""Headless tests for Phase 9 progression: extra armor slots, the
wood -> iron -> steel gear ladder, and magic-tier Arcane gear.
"""
import pygame  # noqa: F401

from game.combat import combat_system
from game.combat.projectile import Projectile
from game.core import save_system
from game.core.world_clock import WorldClock
from game.crafting import recipe_registry, smelt_registry
from game.crafting.furnace_system import FurnaceManager
from game.entities.enemy import Enemy
from game.entities import enemy_registry
from game.entities.player import Player
from game.inventory.equipment import SLOTS
from game.items import item_registry
from game.npcs import npc_registry
from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    ARCANE_PICKAXE_FORTUNE_CHANCE, ARCANE_HELM_LIGHT_EMIT,
)
from game.world import lighting
from game.world.world import World


_ARMOR_SLOTS = ("head", "body", "legs", "boots")
_TIER_PREFIXES = ("wood", "iron", "steel")
_SLOT_SUFFIX = {"head": "helmet", "body": "armor", "legs": "greaves", "boots": "boots"}


def test_equipment_has_legs_and_boots_slots():
    assert SLOTS == ("head", "body", "legs", "boots", "accessory")
    player = Player(0, 0)
    assert set(player.equipment.slots) == set(SLOTS)
    assert player.equipment.get("legs") is None
    assert player.equipment.get("boots") is None
    assert player.equipment.get("accessory") == "grapple_hook"


def test_armor_defense_climbs_wood_iron_steel_per_slot():
    for slot in _ARMOR_SLOTS:
        defenses = [
            item_registry.get(f"{prefix}_{_SLOT_SUFFIX[slot]}").defense
            for prefix in _TIER_PREFIXES
        ]
        assert defenses[0] < defenses[1] < defenses[2], slot
        for prefix in _TIER_PREFIXES:
            item = item_registry.get(f"{prefix}_{_SLOT_SUFFIX[slot]}")
            assert item.equip_slot == slot
            recipe = recipe_registry.get(item.id)
            assert recipe.result_item_id == item.id


def test_iron_and_steel_armor_recipes_use_their_bars():
    for slot in _ARMOR_SLOTS:
        iron_ids = {item_id for item_id, _ in recipe_registry.get(f"iron_{_SLOT_SUFFIX[slot]}").ingredients}
        steel_ids = {item_id for item_id, _ in recipe_registry.get(f"steel_{_SLOT_SUFFIX[slot]}").ingredients}
        assert "iron_bar" in iron_ids
        assert "steel_bar" in steel_ids


def test_steel_pickaxe_outmines_iron_and_smelts_from_iron_bars():
    assert item_registry.get("steel_pickaxe").mining_power > item_registry.get("iron_pickaxe").mining_power
    smelt = smelt_registry.get("steel_bar")
    assert smelt.ore_item_id == "iron_bar"
    assert smelt.fuel_item_id == "coal"
    ingredient_ids = {item_id for item_id, _ in recipe_registry.get("steel_pickaxe").ingredients}
    assert "steel_bar" in ingredient_ids


def test_full_wood_set_defense_is_less_than_full_iron_set():
    player_wood = Player(0, 0)
    player_iron = Player(0, 0)
    for slot in _ARMOR_SLOTS:
        wood_id = f"wood_{_SLOT_SUFFIX[slot]}"
        iron_id = f"iron_{_SLOT_SUFFIX[slot]}"
        player_wood.inventory.add_item(wood_id, 1)
        player_iron.inventory.add_item(iron_id, 1)
        assert player_wood.equipment.equip_from_inventory(player_wood.inventory, wood_id)
        assert player_iron.equipment.equip_from_inventory(player_iron.inventory, iron_id)
    assert player_wood.equipment.total_defense() < player_iron.equipment.total_defense()


def test_legs_and_boots_round_trip_through_save():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x)
    player = Player(x * TILE_SIZE, surface_y * TILE_SIZE)
    player.equipment.slots["legs"] = "wood_greaves"
    player.equipment.slots["boots"] = "iron_boots"

    data = save_system.serialize(world, player, WorldClock(), FurnaceManager())
    _, player2, _, _ = save_system.deserialize(data)
    assert player2.equipment.get("legs") == "wood_greaves"
    assert player2.equipment.get("boots") == "iron_boots"
    assert player2.equipment.get("head") is None


def test_blacksmith_sells_steel_pickaxe_above_value():
    offers = {offer.item_id: offer.price for offer in npc_registry.get("blacksmith").shop_stock}
    assert "steel_pickaxe" in offers
    assert offers["steel_pickaxe"] > item_registry.get("steel_pickaxe").value
    assert "wood_greaves" in offers


def test_blacksmith_shop_offers_sit_above_the_close_button():
    from game.rendering.renderer import npc_shop_offer_rect, npc_button_rects
    npc = npc_registry.get("blacksmith")
    last = npc_shop_offer_rect(len(npc.shop_stock) - 1)
    close = npc_button_rects(npc, True)["close"]
    assert last.bottom < close.top


def test_arcane_bar_is_crafted_from_all_three_gem_bars():
    recipe = recipe_registry.get("arcane_bar")
    ingredient_ids = {item_id for item_id, qty in recipe.ingredients}
    assert ingredient_ids == {"topaz_bar", "sapphire_bar", "emerald_bar"}
    assert all(qty == 1 for _, qty in recipe.ingredients)
    assert recipe.result_item_id == "arcane_bar"
    assert item_registry.get("arcane_bar").rarity.value == "epic"


def test_arcane_pickaxe_outmines_steel_and_has_fortune():
    pick = item_registry.get("arcane_pickaxe")
    assert pick.mining_power > item_registry.get("steel_pickaxe").mining_power
    assert pick.fortune_chance == ARCANE_PICKAXE_FORTUNE_CHANCE
    assert pick.fortune_chance > 0
    recipe = recipe_registry.get("arcane_pickaxe")
    assert "arcane_bar" in {item_id for item_id, _ in recipe.ingredients}


def test_arcane_pickaxe_fortune_doubles_a_drop_on_a_hit():
    player = Player(0, 0)
    player.inventory.slots[0].item_id = "arcane_pickaxe"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    assert player.mining_drop_quantity(rng=lambda: 0.0) == 2
    assert player.mining_drop_quantity(rng=lambda: 0.99) == 1
    player.inventory.slots[0].item_id = "wood_pickaxe"
    assert player.mining_drop_quantity(rng=lambda: 0.0) == 1


def test_arcane_staff_is_a_no_ammo_magic_weapon():
    staff = item_registry.get("arcane_staff")
    assert staff.is_weapon and staff.is_ranged and staff.uses_magic
    assert staff.ammo_item_id is None
    recipe = recipe_registry.get("arcane_staff")
    assert "arcane_bar" in {item_id for item_id, _ in recipe.ingredients}


def test_arcane_staff_fires_without_arrows_and_skips_gravity():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    player.inventory.add_item("arcane_staff", 1)
    staff_index = next(i for i, slot in enumerate(player.inventory.slots) if slot.item_id == "arcane_staff")
    player.inventory.select_hotbar(staff_index)

    bolt = combat_system.try_attack(
        player, world, [], (player.center_x + 80, player.center_y),
    )
    assert isinstance(bolt, Projectile)
    assert bolt.uses_magic is True
    assert bolt.affected_by_gravity is False
    assert player.inventory.count_item("arrow") == 0

    start_y_vel = bolt.y_vel
    combat_system.update_projectiles(player, [bolt], world, [], dt=1 / 60)
    assert bolt.y_vel == start_y_vel


def test_arcane_staff_hit_grants_magic_xp_not_attack_xp():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemy = Enemy(enemy_registry.get("slime"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    bolt = Projectile(
        enemy.center_x, enemy.center_y, 0.0, 0.0, damage=4.0,
        uses_magic=True, affected_by_gravity=False,
    )
    combat_system.update_projectiles(player, [bolt], world, [enemy], dt=1 / 60)
    assert player.skills.xp("magic") > 0.0
    assert player.skills.xp("attack") == 0.0


def test_summoner_cannot_fire_the_arcane_staff():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE, class_id="summoner")
    player.inventory.add_item("arcane_staff", 1)
    staff_index = next(i for i, slot in enumerate(player.inventory.slots) if slot.item_id == "arcane_staff")
    player.inventory.select_hotbar(staff_index)
    assert combat_system.try_attack(
        player, world, [], (player.center_x + 80, player.center_y),
    ) is None


def test_arcane_helmet_outdefends_steel_and_emits_light():
    helm = item_registry.get("arcane_helmet")
    assert helm.defense > item_registry.get("steel_helmet").defense
    assert helm.light_emit == ARCANE_HELM_LIGHT_EMIT
    assert helm.light_emit > 0
    player = Player(0, 0)
    assert player.equipment.total_light_emit() == 0
    player.inventory.add_item("arcane_helmet", 1)
    assert player.equipment.equip_from_inventory(player.inventory, "arcane_helmet")
    assert player.equipment.total_light_emit() == ARCANE_HELM_LIGHT_EMIT
    ambient = 0.04
    dark = lighting.light_level_at(0.0, 0.0, [], ambient)
    lit = lighting.light_level_at(0.0, 0.0, [(0.0, 0.0, ARCANE_HELM_LIGHT_EMIT / 15.0)], ambient)
    assert lit > dark
