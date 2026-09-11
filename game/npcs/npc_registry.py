"""Central, data-driven table of every NPC.

Adding an NPC means adding one NpcDef here; npc_spawner, the dialogue/
shop panel, and the renderer all list whatever is registered. Shop stock
must reference items that already exist in item_registry, and each
ShopOffer.price must be strictly greater than that item's value so
buying then selling can't print coins.
"""
from typing import Dict, List

from game.npcs.npc_def import NpcDef, ShopOffer

_NPCS: Dict[str, NpcDef] = {}


def _register(npc: NpcDef) -> None:
    if npc.id in _NPCS:
        raise ValueError(f"Duplicate NPC id {npc.id}")
    _NPCS[npc.id] = npc


_register(NpcDef(
    id="guide",
    name="Guide",
    color=(80, 175, 110),
    sprite_character_id="mask_dude",
    spawn_condition="always",
    dialogue=(
        "Welcome. I'm the Guide -- I'll keep this short.",
        "Mine with a pickaxe (left-click). Chop trees for wood. Press C to craft.",
        "A Workbench unlocks better recipes; a Furnace smelts ore into bars.",
        "Houses like this one appear across the world. Chests inside hold rare loot.",
        "Press K for Skills -- fighting, mining and crafting all make you stronger.",
        "Other townsfolk show up once you've gathered some loot, or smelted an Iron Bar.",
    ),
))

_register(NpcDef(
    id="merchant",
    name="Merchant",
    color=(220, 175, 55),
    sprite_character_id="pink_man",
    spawn_condition="wealth",
    dialogue=(
        "Got coin? I've got supplies. Click Shop to browse.",
        "I'll buy most anything you're carrying -- click an item on the right to sell it.",
        "Prices are marked up from what I'd pay you. That's the trade.",
    ),
    shop_stock=(
        ShopOffer(item_id="torch", price=8),
        ShopOffer(item_id="arrow", price=3),
        ShopOffer(item_id="apple", price=6),
        ShopOffer(item_id="wood", price=4),
        ShopOffer(item_id="healing_potion", price=14),  # value 8; markup so buy-then-sell can't print coins
    ),
))

_register(NpcDef(
    id="blacksmith",
    name="Blacksmith",
    color=(160, 95, 70),
    sprite_character_id="virtual_guy",
    spawn_condition="discovered_item",
    spawn_item_id="iron_bar",
    dialogue=(
        "You know iron. Good. I sell tools and armor -- click Shop.",
        "Cheaper to craft it yourself if you've got the materials. I'm here when you don't.",
        "I'll buy your extras too. Same deal as the Merchant.",
    ),
    shop_stock=(
        ShopOffer(item_id="wood_sword", price=25),
        ShopOffer(item_id="wood_helmet", price=32),
        ShopOffer(item_id="wood_armor", price=55),
        ShopOffer(item_id="wood_greaves", price=36),
        ShopOffer(item_id="iron_pickaxe", price=90),
        ShopOffer(item_id="steel_pickaxe", price=140),
        ShopOffer(item_id="cactus_jerkin", price=60),  # value 36; desert body piece between wood and iron
    ),
))


GUIDE_ID = "guide"
MERCHANT_ID = "merchant"
BLACKSMITH_ID = "blacksmith"


def get(npc_id: str) -> NpcDef:
    return _NPCS[npc_id]


def all_npcs() -> List[NpcDef]:
    return list(_NPCS.values())
