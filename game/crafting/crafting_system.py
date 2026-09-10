"""Crafting rules: whether a recipe can be made right now, and making it.

Kept separate from Inventory/World/Player so the UI layer (renderer/input)
never has to know how station-proximity or ingredient-checking works.

Two ways to actually craft: craft()/craft_and_discover() are instant (used
by tests and anywhere else that wants a synchronous transaction), while
start_craft()/update_pending_craft() are the timed path the crafting
screen itself uses (see CraftJob) -- ingredients are consumed immediately,
same as starting a smelt, but the result isn't granted until craft_time_for
seconds have passed, so crafting has some real weight to it instead of
resolving the instant you click.
"""
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from game.crafting.recipe import RecipeDef
from game.crafting import recipe_registry
from game.inventory.inventory import Inventory
from game.items import item_registry
from game.items.item import ItemRarity
from game.settings import TILE_SIZE, STATION_SEARCH_RADIUS_TILES, CRAFTING_XP_PER_CRAFT, CRAFTING_RESOURCEFUL_CHANCE
from game.world.world import World

# How long a timed craft (start_craft/update_pending_craft) takes, keyed by
# the result item's existing rarity tier rather than a new per-recipe
# field -- every recipe gets a sensible, automatically-tiered time for
# free, and it matches the same tier the crafting screen/inventory already
# border items by (wood-tier commons are quick, Arcane-tier epics take a
# real beat).
CRAFT_TIME_BY_RARITY = {
    ItemRarity.COMMON: 0.4,
    ItemRarity.UNCOMMON: 0.8,
    ItemRarity.RARE: 1.4,
    ItemRarity.EPIC: 2.2,
}


def craft_time_for(recipe: RecipeDef) -> float:
    return CRAFT_TIME_BY_RARITY[item_registry.get(recipe.result_item_id).rarity]


@dataclass
class CraftJob:
    recipe_id: str
    remaining_s: float
    total_s: float


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


def _apply_craft_rewards(recipe: RecipeDef, player) -> List[RecipeDef]:
    """Discovery + Crafting XP + the crafting_resourceful refund roll --
    shared by the instant craft_and_discover() path and the timed
    start_craft()/update_pending_craft() path below, so a craft grants
    identical rewards either way. Assumes the result has already been
    granted to the inventory."""
    before = _discovered_recipe_ids(player.discovered_item_ids)
    player.discovered_item_ids.add(recipe.result_item_id)
    player.skills.add_xp("crafting", CRAFTING_XP_PER_CRAFT * player.skills.crafting_xp_multiplier())
    if player.skills.has_node("crafting_resourceful") and random.random() < CRAFTING_RESOURCEFUL_CHANCE:
        refund_item_id, refund_qty = random.choice(recipe.ingredients)
        player.inventory.add_item(refund_item_id, refund_qty)
    return _newly_discovered_recipes(before, player.discovered_item_ids)


def craft_and_discover(recipe: RecipeDef, player, world: World):
    """Like craft(), but on success also marks recipe.result_item_id as
    discovered (crafting something for the first time counts as having
    obtained it), grants Crafting XP (boosted by the Crafting skill's own
    "crafting_master" node), rolls a "crafting_resourceful" ingredient
    refund if that node is unlocked, and returns any further recipes that
    just became discovered as a result. Returns (success, newly_discovered_recipes).
    Instant -- see the module docstring for the timed alternative the
    crafting screen actually uses."""
    if not craft(recipe, player.inventory, world, player.center_x, player.center_y):
        return False, []
    return True, _apply_craft_rewards(recipe, player)


def start_craft(recipe: RecipeDef, player, world: World) -> bool:
    """Begins a timed craft: validates + consumes ingredients immediately
    (like FurnaceManager.start_smelt does for ore/fuel), but the result
    isn't granted until update_pending_craft's timer elapses. Only one
    craft can be in progress at a time (Player.craft_job) -- a player only
    has two hands. Returns whether it actually started."""
    if player.craft_job is not None:
        return False
    if not can_craft(recipe, player.inventory, world, player.center_x, player.center_y):
        return False
    for item_id, qty in recipe.ingredients:
        player.inventory.remove_item(item_id, qty)
    total_s = craft_time_for(recipe)
    player.craft_job = CraftJob(recipe_id=recipe.id, remaining_s=total_s, total_s=total_s)
    return True


def update_pending_craft(player, dt: float) -> Tuple[Optional[RecipeDef], List[RecipeDef]]:
    """Advances the player's in-progress craft job, if any. The instant
    its timer elapses, grants the result and applies _apply_craft_rewards,
    returning (the finished RecipeDef, any newly-discovered recipes);
    (None, []) every other frame, including when nothing is in progress."""
    if player.craft_job is None:
        return None, []
    player.craft_job.remaining_s -= dt
    if player.craft_job.remaining_s > 0.0:
        return None, []
    recipe = recipe_registry.get(player.craft_job.recipe_id)
    player.craft_job = None
    player.collect_item(recipe.result_item_id, recipe.result_quantity)
    newly_discovered = _apply_craft_rewards(recipe, player)
    return recipe, newly_discovered


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
