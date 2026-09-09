"""Central, data-driven table of every smelting recipe (add ore->bar pairs
here). Mirrors recipe_registry.py's shape, but for the furnace's
started-then-collected transaction instead of an instant craft."""
from typing import Dict, List

from game.crafting.smelt_recipe import SmeltRecipeDef
from game.settings import SMELT_TIME_IRON_S, SMELT_TIME_GEM_S

_RECIPES: Dict[str, SmeltRecipeDef] = {}


def _register(recipe: SmeltRecipeDef) -> None:
    if recipe.id in _RECIPES:
        raise ValueError(f"Duplicate smelt recipe id {recipe.id}")
    _RECIPES[recipe.id] = recipe


_register(SmeltRecipeDef(
    id="iron_bar", name="Iron Bar",
    ore_item_id="iron_ore", ore_quantity=2,
    fuel_item_id="coal", fuel_quantity=1,
    bar_item_id="iron_bar", bar_quantity=1,
    smelt_time_s=SMELT_TIME_IRON_S,
))

_register(SmeltRecipeDef(
    id="topaz_bar", name="Topaz Bar",
    ore_item_id="topaz", ore_quantity=1,
    fuel_item_id="coal", fuel_quantity=1,
    bar_item_id="topaz_bar", bar_quantity=1,
    smelt_time_s=SMELT_TIME_GEM_S,
))

_register(SmeltRecipeDef(
    id="sapphire_bar", name="Sapphire Bar",
    ore_item_id="sapphire", ore_quantity=1,
    fuel_item_id="coal", fuel_quantity=1,
    bar_item_id="sapphire_bar", bar_quantity=1,
    smelt_time_s=SMELT_TIME_GEM_S,
))

_register(SmeltRecipeDef(
    id="emerald_bar", name="Emerald Bar",
    ore_item_id="emerald", ore_quantity=1,
    fuel_item_id="coal", fuel_quantity=1,
    bar_item_id="emerald_bar", bar_quantity=1,
    smelt_time_s=SMELT_TIME_GEM_S,
))


def get(recipe_id: str) -> SmeltRecipeDef:
    return _RECIPES[recipe_id]


def all_recipes() -> List[SmeltRecipeDef]:
    return list(_RECIPES.values())
