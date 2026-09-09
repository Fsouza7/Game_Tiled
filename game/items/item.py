"""Item schema shared by every item in the game.

Phase 1 needed enough to make mining/building/inventory work (max_stack,
tool fields, places_tile_id). Phase 2 added the full data model for the
item system: category, description, icon, rarity, value, damage, speed and
durability. Phase 4 added combat fields (is_weapon/is_ranged/ammo_item_id).
An equipment pass (still Phase 4-adjacent, added on user request ahead of
the formal Phase 9 progression work) added equip_slot/defense for armor.
A later pass added heal_amount and a real "eat" action (Player.eat_selected,
bound to F) for food items -- an item's category alone still doesn't imply
a usage mechanic exists (e.g. `arrow` is CONSUMABLE but not edible); see
item_registry.py's module docstring for exactly what's wired up.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ItemCategory(Enum):
    BLOCK = "block"
    ORE = "ore"
    MATERIAL = "material"
    TOOL = "tool"
    WEAPON = "weapon"
    CONSUMABLE = "consumable"
    ARMOR = "armor"
    DECORATION = "decoration"


class ItemRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    description: str
    category: ItemCategory
    max_stack: int
    rarity: ItemRarity = ItemRarity.COMMON
    value: int = 0
    damage: float = 0.0
    speed: float = 0.0
    max_durability: Optional[int] = None  # None = does not degrade

    # Icon resolution order (see game/rendering/renderer.py):
    # places_tile_id -> icon_tile_id -> icon_key (assets.py's static/
    # procedural icon table) -> flat color swatch for the category.
    # icon_tile_id lets a non-placeable item (an ore, raw wood) borrow a
    # tile's texture for its icon without implying it can be placed.
    icon_tile_id: Optional[int] = None
    icon_key: Optional[str] = None

    # --- mining/building fields (Phase 1) ---
    is_tool: bool = False
    mining_power: float = 0.0  # damage per mining tick, tools only
    tool_type: Optional[str] = None  # matches TileDef.required_tool
    places_tile_id: Optional[int] = None  # set for block/decoration items

    # --- combat fields (Phase 4) ---
    is_weapon: bool = False
    is_ranged: bool = False  # False = melee (hitbox in front of the player)
    ammo_item_id: Optional[str] = None  # required in inventory to fire, ranged only

    # --- equipment fields ---
    equip_slot: Optional[str] = None  # e.g. "head"/"body" -- which Equipment slot this fits
    defense: float = 0.0  # flat damage reduction while equipped

    # --- consumable fields ---
    heal_amount: float = 0.0  # HP restored on eating; 0 = not edible
