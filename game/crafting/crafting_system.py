"""Crafting rules: whether a recipe can be made right now, and making it.

Kept separate from Inventory/World/Player so the UI layer (renderer/input)
never has to know how station-proximity or ingredient-checking works.
"""
import random
from typing import List

from game.crafting.recipe import RecipeDef
from game.crafting import recipe_registry
from game.inventory.inventory import Inventory
from game.settings import TILE_SIZE, STATION_SEARCH_RADIUS_TILES, CRAFTING_XP_PER_CRAFT, CRAFTING_RESOURCEFUL_CHANCE
from game.world.world import World


def is_near_station(world: World, center_x_px: float, center_y_px: float, station_tile_id: int) -> bool:
    center_tx = int(center_x_px // TILE_SIZE)
    center_ty = int(center_y_px // TILE_SIZE)
    radius = STATION_SEARCH_RADIUS_TILES
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if world.get_tile(center_tx + dx, center_ty + dy) == station_tile_id:
                return True
    return False


def has_ingredients(recipe: RecipeDef, inventory: Inventory) -> bool:
    return all(inventory.count_item(item_id) >= qty for item_id, qty in recipe.ingredients)


def is_recipe_discovered(recipe: RecipeDef, discovered_item_ids) -> bool:
    """A recipe is "discovered" once the player has ever obtained every one
    of its ingredients at least once (see Player.discovered_item_ids /
    collect_item) -- not just currently holding them. Undiscovered recipes
    still appear in the crafting screen, but as a "???" placeholder (see
    renderer.py): you learn a recipe exists by finding what it's made of."""
    return all(item_id in discovered_item_ids for item_id, _ in recipe.ingredients)


def undiscovered_ingredients(recipe: RecipeDef, discovered_item_ids):
    """The ingredient item ids of `recipe` the player hasn't found yet --
    used to tell them specifically what's still missing (see README "How
    recipe discovery works")."""
    return [item_id for item_id, _ in recipe.ingredients if item_id not in discovered_item_ids]


def _discovered_recipe_ids(discovered_item_ids) -> set:
    return {
        recipe.id for recipe in recipe_registry.all_recipes()
        if is_recipe_discovered(recipe, discovered_item_ids)
    }


def _newly_discovered_recipes(before_ids: set, discovered_item_ids) -> List[RecipeDef]:
    return [
        recipe for recipe in recipe_registry.all_recipes()
        if recipe.id not in before_ids and is_recipe_discovered(recipe, discovered_item_ids)
    ]


def mark_discovered(player, item_id: str) -> List[RecipeDef]:
    """Marks item_id discovered without adding it to the inventory -- for
    call sites that already granted the item themselves (e.g. a shop buy
    that had to handle an inventory-full refund). Returns any recipes that
    just became fully discovered as a result."""
    before = _discovered_recipe_ids(player.discovered_item_ids)
    player.discovered_item_ids.add(item_id)
    return _newly_discovered_recipes(before, player.discovered_item_ids)


def collect_and_discover(player, item_id: str, quantity: int) -> List[RecipeDef]:
    """Adds item_id to the player's inventory (via Player.collect_item,
    which marks it discovered) and returns any recipes that just became
    fully discovered as a result -- i.e. this item was their last missing
    ingredient. Callers (InputHandler, GameApp) push these as
    notifications. Cheap: recipe_registry is small (~20 entries)."""
    before = _discovered_recipe_ids(player.discovered_item_ids)
    player.collect_item(item_id, quantity)
    return _newly_discovered_recipes(before, player.discovered_item_ids)


def craft_and_discover(recipe: RecipeDef, player, world: World):
    """Like craft(), but on success also marks recipe.result_item_id as
    discovered (crafting something for the first time counts as having
    obtained it), grants Crafting XP (boosted by the Crafting skill's own
    "crafting_master" node), rolls a "crafting_resourceful" ingredient
    refund if that node is unlocked, and returns any further recipes that
    just became discovered as a result. Returns (success, newly_discovered_recipes)."""
    before = _discovered_recipe_ids(player.discovered_item_ids)
    if not craft(recipe, player.inventory, world, player.center_x, player.center_y):
        return False, []
    player.discovered_item_ids.add(recipe.result_item_id)
    player.skills.add_xp("crafting", CRAFTING_XP_PER_CRAFT * player.skills.crafting_xp_multiplier())
    if player.skills.has_node("crafting_resourceful") and random.random() < CRAFTING_RESOURCEFUL_CHANCE:
        refund_item_id, refund_qty = random.choice(recipe.ingredients)
        player.inventory.add_item(refund_item_id, refund_qty)
    return True, _newly_discovered_recipes(before, player.discovered_item_ids)


def can_craft(recipe: RecipeDef, inventory: Inventory, world: World, player_center_x: float, player_center_y: float) -> bool:
    if not has_ingredients(recipe, inventory):
        return False
    if recipe.station_tile_id is not None:
        return is_near_station(world, player_center_x, player_center_y, recipe.station_tile_id)
    return True


def craft(recipe: RecipeDef, inventory: Inventory, world: World, player_center_x: float, player_center_y: float) -> bool:
    """Attempts the recipe. Returns whether it succeeded. Never partially
    consumes ingredients: if the result can't fit in the inventory, nothing
    is spent."""
    if not can_craft(recipe, inventory, world, player_center_x, player_center_y):
        return False

    for item_id, qty in recipe.ingredients:
        inventory.remove_item(item_id, qty)

    leftover = inventory.add_item(recipe.result_item_id, recipe.result_quantity)
    if leftover > 0:
        # Result didn't fully fit (inventory full) -- undo the craft.
        inventory.remove_item(recipe.result_item_id, recipe.result_quantity - leftover)
        for item_id, qty in recipe.ingredients:
            inventory.add_item(item_id, qty)
        return False
    return True
