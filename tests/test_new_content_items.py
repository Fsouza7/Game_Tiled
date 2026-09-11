"""Headless tests for the dead-end-material sink pass: a craftable healing
potion, cactus body armor, a feather charm, and three gem-bar rings so
Topaz/Sapphire/Emerald Bars have a use besides the Arcane Bar. Shop
markups must stay strictly above ItemDef.value (buy-then-sell can't
print coins). Icons must resolve in load_static_item_icons.
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, PLAYER_MOVE_SPEED
from game.entities.player import Player
from game.crafting import recipe_registry, crafting_system
from game.items import item_registry
from game.items.item import ItemCategory, ItemRarity
from game.npcs import npc_registry
from game.world.world import World
from game.world.tile_registry import WORKBENCH_ID, AIR_ID


_NEW_ITEM_IDS = (
    "healing_potion", "cactus_jerkin", "feather_charm",
    "topaz_ring", "sapphire_ring", "emerald_ring",
)


def _make_player(world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _find_clear_air_column(world: World, near_x: int, search_radius: int = 40) -> int:
    for offset in range(search_radius):
        for x in (near_x + offset, near_x - offset):
            if 0 <= x < WORLD_WIDTH_TILES:
                surface_y = world.surface_spawn_y(x) + 1
                if world.get_tile(x, surface_y - 1) == AIR_ID:
                    return x
    raise AssertionError("no clear surface column found near_x for placing a workbench")


def _give_ingredients(player, recipe):
    for item_id, qty in recipe.ingredients:
        player.inventory.add_item(item_id, qty)


def _place_workbench_near_player(world, player):
    x = _find_clear_air_column(world, int(player.center_x // TILE_SIZE))
    surface_y = world.surface_spawn_y(x) + 1
    assert world.try_place_tile(x, surface_y - 1, WORKBENCH_ID)
    player.x = x * TILE_SIZE
    player.y = (surface_y - 1) * TILE_SIZE
    return x


# --- Registration / stats ---

def test_new_items_are_registered_with_the_expected_slots_and_stats():
    potion = item_registry.get("healing_potion")
    assert potion.category == ItemCategory.CONSUMABLE
    assert potion.heal_amount == 40.0
    assert potion.rarity == ItemRarity.UNCOMMON
    assert potion.value == 8

    jerkin = item_registry.get("cactus_jerkin")
    assert jerkin.category == ItemCategory.ARMOR
    assert jerkin.equip_slot == "body"
    assert jerkin.defense == 8.0
    assert jerkin.rarity == ItemRarity.UNCOMMON
    wood_body = item_registry.get("wood_armor").defense
    iron_body = item_registry.get("iron_armor").defense
    assert wood_body < jerkin.defense < iron_body
    assert jerkin.defense < item_registry.get("voidsteel_armor").defense

    charm = item_registry.get("feather_charm")
    assert charm.category == ItemCategory.ACCESSORY
    assert charm.equip_slot == "accessory"
    assert charm.accessory_kind is None
    assert charm.move_speed_bonus == 0.5
    assert charm.defense == 1.0
    assert charm.rarity == ItemRarity.COMMON
    assert charm.move_speed_bonus < PLAYER_MOVE_SPEED
    assert charm.move_speed_bonus < item_registry.get("swift_anklet").move_speed_bonus

    topaz = item_registry.get("topaz_ring")
    assert topaz.category == ItemCategory.ACCESSORY
    assert topaz.equip_slot == "accessory"
    assert topaz.crit_chance == 0.05
    assert topaz.rarity == ItemRarity.UNCOMMON
    assert topaz.crit_chance < item_registry.get("arcane_sword").crit_chance

    sapphire = item_registry.get("sapphire_ring")
    assert sapphire.category == ItemCategory.ACCESSORY
    assert sapphire.equip_slot == "accessory"
    assert sapphire.defense == 4.0
    assert sapphire.light_emit == 8
    assert sapphire.rarity == ItemRarity.UNCOMMON
    assert sapphire.defense < item_registry.get("voidstone_amulet").defense
    assert sapphire.light_emit < item_registry.get("voidstone_amulet").light_emit

    emerald = item_registry.get("emerald_ring")
    assert emerald.category == ItemCategory.ACCESSORY
    assert emerald.equip_slot == "accessory"
    assert emerald.move_speed_bonus == 0.8
    assert emerald.rarity == ItemRarity.UNCOMMON
    assert emerald.move_speed_bonus < item_registry.get("arcane_anklet").move_speed_bonus


def test_eating_a_healing_potion_heals_and_consumes_it():
    _, player = _make_player()
    player.health = 50.0
    player.inventory.slots[0].item_id = "healing_potion"
    player.inventory.slots[0].quantity = 2
    player.inventory.select_hotbar(0)

    assert player.eat_selected() is True
    assert player.health == 50.0 + item_registry.get("healing_potion").heal_amount
    assert player.inventory.slots[0].quantity == 1


# --- Recipes ---

def test_new_recipes_reference_real_items_with_positive_quantities():
    for recipe_id in _NEW_ITEM_IDS:
        recipe = recipe_registry.get(recipe_id)
        assert recipe.result_item_id == recipe_id
        item_registry.get(recipe.result_item_id)
        assert recipe.result_quantity > 0
        for item_id, qty in recipe.ingredients:
            item_registry.get(item_id)
            assert qty > 0


def test_healing_potion_and_feather_charm_craft_anywhere():
    world, player = _make_player()  # no workbench
    for recipe_id in ("healing_potion", "feather_charm"):
        recipe = recipe_registry.get(recipe_id)
        assert recipe.station_tile_id is None
        _give_ingredients(player, recipe)
        assert crafting_system.can_craft(
            recipe, player.inventory, world, player.center_x, player.center_y,
        )
        assert crafting_system.craft(
            recipe, player.inventory, world, player.center_x, player.center_y,
        )
        assert player.inventory.count_item(recipe.result_item_id) == recipe.result_quantity


def test_workbench_recipes_craft_near_a_workbench_and_not_away_from_one():
    world, player = _make_player()
    for recipe_id in ("cactus_jerkin", "topaz_ring", "sapphire_ring", "emerald_ring"):
        recipe = recipe_registry.get(recipe_id)
        assert recipe.station_tile_id == WORKBENCH_ID
        _give_ingredients(player, recipe)
        assert crafting_system.has_ingredients(recipe, player.inventory)
        assert not crafting_system.can_craft(
            recipe, player.inventory, world, player.center_x, player.center_y,
        )

    _place_workbench_near_player(world, player)
    for recipe_id in ("cactus_jerkin", "topaz_ring", "sapphire_ring", "emerald_ring"):
        recipe = recipe_registry.get(recipe_id)
        # Re-give in case a previous loop already consumed (it didn't --
        # can_craft failed without a station -- but keep the test robust
        # if ingredient leftovers ever change).
        if player.inventory.count_item(recipe.result_item_id) == 0:
            _give_ingredients(player, recipe)
        assert crafting_system.can_craft(
            recipe, player.inventory, world, player.center_x, player.center_y,
        )
        assert crafting_system.craft(
            recipe, player.inventory, world, player.center_x, player.center_y,
        )
        assert player.inventory.count_item(recipe.result_item_id) >= 1


def test_gem_ring_recipes_consume_the_matching_gem_bar():
    expected = {
        "topaz_ring": "topaz_bar",
        "sapphire_ring": "sapphire_bar",
        "emerald_ring": "emerald_bar",
    }
    for recipe_id, bar_id in expected.items():
        ingredient_ids = {item_id for item_id, _ in recipe_registry.get(recipe_id).ingredients}
        assert bar_id in ingredient_ids
        assert "iron_bar" in ingredient_ids


def test_cactus_jerkin_recipe_uses_cactus_fiber():
    ingredient_ids = {item_id for item_id, _ in recipe_registry.get("cactus_jerkin").ingredients}
    assert "cactus_fiber" in ingredient_ids
    assert "wood" in ingredient_ids


# --- Shops ---

def test_merchant_sells_healing_potion_above_value():
    potion = item_registry.get("healing_potion")
    offers = {offer.item_id: offer.price for offer in npc_registry.get("merchant").shop_stock}
    assert "healing_potion" in offers
    assert offers["healing_potion"] > potion.value


def test_blacksmith_sells_cactus_jerkin_above_value():
    jerkin = item_registry.get("cactus_jerkin")
    offers = {offer.item_id: offer.price for offer in npc_registry.get("blacksmith").shop_stock}
    assert "cactus_jerkin" in offers
    assert offers["cactus_jerkin"] > jerkin.value


def test_new_shop_offers_do_not_break_price_above_value_invariant():
    for npc in npc_registry.all_npcs():
        for offer in npc.shop_stock:
            item_def = item_registry.get(offer.item_id)
            assert offer.price > item_def.value, (
                f"{npc.id} sells {offer.item_id} at {offer.price} "
                f"which isn't above value {item_def.value}"
            )


# --- Icons ---

def test_new_item_icons_resolve_in_load_static_item_icons():
    # convert_alpha() (used by load_static_item_icons) needs a display
    # surface even under the dummy SDL driver -- same pattern as
    # test_deferred_assets_pass2 / test_grapple_hook.
    pygame.display.set_mode((1, 1))
    from game.rendering import assets
    icons = assets.load_static_item_icons()
    for item_id in _NEW_ITEM_IDS:
        icon_key = item_registry.get(item_id).icon_key
        assert icon_key in icons, f"{item_id} icon_key {icon_key!r} missing from load_static_item_icons"
        surface = icons[icon_key]
        assert surface.get_width() > 0 and surface.get_height() > 0
