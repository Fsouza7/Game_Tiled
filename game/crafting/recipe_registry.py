"""Central, data-driven table of every crafting recipe. Adding a recipe
means adding one entry here -- no other file needs to change (see README
"Como criar uma receita").
"""
from typing import Dict, List

from game.crafting.recipe import RecipeDef
from game.world.tile_registry import WORKBENCH_ID

_RECIPES: Dict[str, RecipeDef] = {}


def _register(recipe: RecipeDef) -> None:
    if recipe.id in _RECIPES:
        raise ValueError(f"Duplicate recipe id {recipe.id}")
    _RECIPES[recipe.id] = recipe


_register(RecipeDef(
    id="workbench", name="Workbench",
    ingredients=(("wood", 10),),
    result_item_id="workbench", result_quantity=1,
    station_tile_id=None,  # craftable anywhere, by hand
))

_register(RecipeDef(
    id="wood_plank_block", name="Wood Plank",
    ingredients=(("wood", 1),),
    result_item_id="wood_plank_block", result_quantity=4,
    station_tile_id=None,
))

_register(RecipeDef(
    id="wood_pickaxe", name="Wood Pickaxe",
    ingredients=(("wood", 5),),
    result_item_id="wood_pickaxe", result_quantity=1,
    station_tile_id=None,  # lets the player remake their starter tool if lost
))

_register(RecipeDef(
    id="stone_pickaxe", name="Stone Pickaxe",
    ingredients=(("wood", 5), ("stone_block", 10)),
    result_item_id="stone_pickaxe", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_pickaxe", name="Iron Pickaxe",
    ingredients=(("wood", 3), ("iron_bar", 3)),
    result_item_id="iron_pickaxe", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="furnace", name="Furnace",
    ingredients=(("stone_block", 12), ("coal", 2)),
    result_item_id="furnace", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="wood_sword", name="Wood Sword",
    ingredients=(("wood", 8),),
    result_item_id="wood_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="wood_bow", name="Wood Bow",
    ingredients=(("wood", 10), ("slime_gel", 3)),
    result_item_id="wood_bow", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arrow", name="Arrow",
    ingredients=(("wood", 1),),
    result_item_id="arrow", result_quantity=5,
    station_tile_id=None,
))

_register(RecipeDef(
    id="summon_rod_wood", name="Twig Rod",
    ingredients=(("wood", 8),),
    result_item_id="summon_rod_wood", result_quantity=1,
    station_tile_id=None,  # lets a Summoner remake their starter rod if lost
))

_register(RecipeDef(
    id="summon_rod_iron", name="Iron Rod",
    ingredients=(("iron_bar", 3), ("wood", 5), ("slime_gel", 2)),
    result_item_id="summon_rod_iron", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="wood_helmet", name="Wood Helmet",
    ingredients=(("wood", 8),),
    result_item_id="wood_helmet", result_quantity=1,
    station_tile_id=None,
))

_register(RecipeDef(
    id="wood_armor", name="Wood Armor",
    ingredients=(("wood", 15),),
    result_item_id="wood_armor", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="grapple_hook", name="Grapple Hook",
    ingredients=(("iron_bar", 2), ("wood", 4), ("slime_gel", 2)),
    result_item_id="grapple_hook", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="torch", name="Torch",
    ingredients=(("wood", 1), ("coal", 1)),
    result_item_id="torch", result_quantity=3,
    station_tile_id=None,
))

_register(RecipeDef(
    id="arrow_cactus", name="Arrow (Cactus Fletching)",
    ingredients=(("cactus_fiber", 2),),
    result_item_id="arrow", result_quantity=5,
    station_tile_id=None,  # a desert-friendly alternative to the wood recipe
))

_register(RecipeDef(
    id="trampoline", name="Trampoline",
    ingredients=(("wood", 6), ("slime_gel", 3)),
    result_item_id="trampoline", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="checkpoint", name="Checkpoint",
    ingredients=(("stone_block", 8), ("wood", 4)),
    result_item_id="checkpoint", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))


def get(recipe_id: str) -> RecipeDef:
    return _RECIPES[recipe_id]


def all_recipes() -> List[RecipeDef]:
    return list(_RECIPES.values())
