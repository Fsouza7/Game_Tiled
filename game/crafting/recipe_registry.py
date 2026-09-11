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
    id="steel_pickaxe", name="Steel Pickaxe",
    ingredients=(("wood", 3), ("steel_bar", 3)),
    result_item_id="steel_pickaxe", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_bar", name="Arcane Bar",
    ingredients=(("topaz_bar", 1), ("sapphire_bar", 1), ("emerald_bar", 1)),
    result_item_id="arcane_bar", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_pickaxe", name="Arcane Pickaxe",
    ingredients=(("wood", 3), ("arcane_bar", 3)),
    result_item_id="arcane_pickaxe", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_staff", name="Arcane Staff",
    ingredients=(("wood", 5), ("arcane_bar", 2)),
    result_item_id="arcane_staff", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_sword", name="Arcane Sword",
    ingredients=(("wood", 3), ("arcane_bar", 3)),
    result_item_id="arcane_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="summon_rod_arcane", name="Arcane Rod",
    ingredients=(("arcane_bar", 3), ("wood", 5)),
    result_item_id="summon_rod_arcane", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="furnace", name="Furnace",
    ingredients=(("stone_block", 12), ("coal", 2)),
    result_item_id="furnace", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="personal_chest", name="Personal Chest",
    ingredients=(("wood", 8),),
    result_item_id="personal_chest", result_quantity=1,
    station_tile_id=None,
))

_register(RecipeDef(
    id="wood_sword", name="Wood Sword",
    ingredients=(("wood", 8),),
    result_item_id="wood_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_sword", name="Iron Sword",
    ingredients=(("wood", 4), ("iron_bar", 3)),
    result_item_id="iron_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_sword", name="Steel Sword",
    ingredients=(("wood", 4), ("steel_bar", 3)),
    result_item_id="steel_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="wood_bow", name="Wood Bow",
    ingredients=(("wood", 10), ("slime_gel", 3)),
    result_item_id="wood_bow", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_bow", name="Iron Bow",
    ingredients=(("wood", 6), ("iron_bar", 3), ("slime_gel", 2)),
    result_item_id="iron_bow", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_bow", name="Steel Bow",
    ingredients=(("wood", 6), ("steel_bar", 3), ("slime_gel", 2)),
    result_item_id="steel_bow", result_quantity=1,
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
    id="summon_rod_steel", name="Steel Rod",
    ingredients=(("steel_bar", 3), ("wood", 5), ("slime_gel", 2)),
    result_item_id="summon_rod_steel", result_quantity=1,
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
    id="wood_greaves", name="Wood Greaves",
    ingredients=(("wood", 10),),
    result_item_id="wood_greaves", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="wood_boots", name="Wood Boots",
    ingredients=(("wood", 6),),
    result_item_id="wood_boots", result_quantity=1,
    station_tile_id=None,
))

_register(RecipeDef(
    id="iron_helmet", name="Iron Helmet",
    ingredients=(("iron_bar", 2), ("wood", 4)),
    result_item_id="iron_helmet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_armor", name="Iron Armor",
    ingredients=(("iron_bar", 4), ("wood", 6)),
    result_item_id="iron_armor", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_greaves", name="Iron Greaves",
    ingredients=(("iron_bar", 3), ("wood", 4)),
    result_item_id="iron_greaves", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="iron_boots", name="Iron Boots",
    ingredients=(("iron_bar", 2), ("wood", 3)),
    result_item_id="iron_boots", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_helmet", name="Steel Helmet",
    ingredients=(("steel_bar", 2), ("wood", 3)),
    result_item_id="steel_helmet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_armor", name="Steel Armor",
    ingredients=(("steel_bar", 4), ("wood", 4)),
    result_item_id="steel_armor", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_greaves", name="Steel Greaves",
    ingredients=(("steel_bar", 3), ("wood", 3)),
    result_item_id="steel_greaves", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="steel_boots", name="Steel Boots",
    ingredients=(("steel_bar", 2), ("wood", 2)),
    result_item_id="steel_boots", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_helmet", name="Arcane Helm",
    ingredients=(("arcane_bar", 2), ("wood", 3)),
    result_item_id="arcane_helmet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

# --- Post-Arcane tier: Voidstone / Voidsteel (endgame) -- ingredient shape
# mirrors the Arcane-tier recipes above, scaled up, using voidsteel_bar in
# place of arcane_bar (see arcane_pickaxe/arcane_staff/arcane_helmet). ---

_register(RecipeDef(
    id="voidsteel_sword", name="Voidsteel Sword",
    ingredients=(("wood", 4), ("voidsteel_bar", 4)),
    result_item_id="voidsteel_sword", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="voidsteel_helmet", name="Voidsteel Helm",
    ingredients=(("voidsteel_bar", 3), ("wood", 3)),
    result_item_id="voidsteel_helmet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="voidsteel_armor", name="Voidsteel Armor",
    ingredients=(("voidsteel_bar", 5), ("wood", 4)),
    result_item_id="voidsteel_armor", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="voidsteel_greaves", name="Voidsteel Greaves",
    ingredients=(("voidsteel_bar", 4), ("wood", 3)),
    result_item_id="voidsteel_greaves", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="voidsteel_boots", name="Voidsteel Boots",
    ingredients=(("voidsteel_bar", 3), ("wood", 2)),
    result_item_id="voidsteel_boots", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="voidstone_amulet", name="Voidstone Amulet",
    ingredients=(("voidsteel_bar", 2), ("voidstone", 2), ("wood", 2)),
    result_item_id="voidstone_amulet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="summon_rod_voidsteel", name="Voidsteel Rod",
    ingredients=(("voidsteel_bar", 4), ("wood", 5), ("slime_gel", 3)),
    result_item_id="summon_rod_voidsteel", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_body", name="Arcane Robe",
    ingredients=(("arcane_bar", 4), ("wood", 4)),
    result_item_id="arcane_body", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_greaves", name="Arcane Greaves",
    ingredients=(("arcane_bar", 3), ("wood", 3)),
    result_item_id="arcane_greaves", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_boots", name="Arcane Boots",
    ingredients=(("arcane_bar", 2), ("wood", 2)),
    result_item_id="arcane_boots", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="grapple_hook", name="Grapple Hook",
    ingredients=(("iron_bar", 2), ("wood", 4), ("slime_gel", 2)),
    result_item_id="grapple_hook", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="warriors_charm", name="Warrior's Charm",
    ingredients=(("steel_bar", 1), ("iron_bar", 2), ("wood", 3)),
    result_item_id="warriors_charm", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="summoners_trinket", name="Summoner's Trinket",
    ingredients=(("iron_bar", 1), ("slime_gel", 4), ("wood", 3)),
    result_item_id="summoners_trinket", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="swift_anklet", name="Swift Anklet",
    ingredients=(("steel_bar", 2), ("feather", 4)),
    result_item_id="swift_anklet", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="arcane_anklet", name="Arcane Anklet",
    ingredients=(("arcane_bar", 2), ("feather", 6)),
    result_item_id="arcane_anklet", result_quantity=1,
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

# --- Building: Doors & Beds (user-requested construction system) ---

_register(RecipeDef(
    id="door", name="Wood Door",
    ingredients=(("wood", 6),),
    result_item_id="door", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="bed", name="Bed",
    ingredients=(("wood", 8), ("wood_plank_block", 4)),
    result_item_id="bed", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

# --- Boss: Slime King (Phase 10) ---

_register(RecipeDef(
    id="slime_core_idol", name="Slime Core Idol",
    ingredients=(("slime_gel", 20), ("iron_bar", 5)),
    result_item_id="slime_core_idol", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="slime_king_crown", name="Crown of the Slime King",
    ingredients=(("slime_king_core", 1), ("steel_bar", 3)),
    result_item_id="slime_king_crown", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="slime_king_fang", name="Fang of the Slime King",
    ingredients=(("slime_king_core", 1), ("steel_bar", 3)),
    result_item_id="slime_king_fang", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="slime_king_bulwark", name="Bulwark of the Slime King",
    ingredients=(("slime_king_core", 1), ("steel_bar", 3)),
    result_item_id="slime_king_bulwark", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))


# --- Biome exclusive mob drops (Frost Hopper / Swamp Mosquito) ---

_register(RecipeDef(
    id="frost_arrows", name="Frost Arrows",
    ingredients=(("frost_shard", 1), ("wood", 1)),
    result_item_id="arrow", result_quantity=8,
    station_tile_id=None,  # ammo both classes can spend, no new ammo type
))

_register(RecipeDef(
    id="wing_charm", name="Wing Charm",
    ingredients=(("mosquito_wing", 4), ("slime_gel", 2)),
    result_item_id="wing_charm", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

# --- Dead-end material sinks + a craftable potion (see item_registry.py's
# matching items). Potion and feather charm are hand-crafts so early
# drops become useful before a Workbench; the jerkin and gem rings need
# one, matching every other body-armor / jewelry recipe. ---

_register(RecipeDef(
    id="healing_potion", name="Healing Potion",
    ingredients=(("apple", 2), ("slime_gel", 1)),
    result_item_id="healing_potion", result_quantity=1,
    station_tile_id=None,  # apples + gel are both early drops; no station gate
))

_register(RecipeDef(
    id="cactus_jerkin", name="Cactus Jerkin",
    ingredients=(("cactus_fiber", 8), ("wood", 4)),
    result_item_id="cactus_jerkin", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="feather_charm", name="Feather Charm",
    ingredients=(("feather", 6), ("wood", 2)),
    result_item_id="feather_charm", result_quantity=1,
    station_tile_id=None,  # duskwing drop sink before a Workbench exists
))

_register(RecipeDef(
    id="topaz_ring", name="Topaz Ring",
    ingredients=(("topaz_bar", 1), ("iron_bar", 1)),
    result_item_id="topaz_ring", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="sapphire_ring", name="Sapphire Ring",
    ingredients=(("sapphire_bar", 1), ("iron_bar", 1)),
    result_item_id="sapphire_ring", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))

_register(RecipeDef(
    id="emerald_ring", name="Emerald Ring",
    ingredients=(("emerald_bar", 1), ("iron_bar", 1)),
    result_item_id="emerald_ring", result_quantity=1,
    station_tile_id=WORKBENCH_ID,
))


def get(recipe_id: str) -> RecipeDef:
    return _RECIPES[recipe_id]


def all_recipes() -> List[RecipeDef]:
    return list(_RECIPES.values())
