"""NpcDef schema: the data every NPC type is built from.

Spawn conditions are named strings resolved by npc_spawner.condition_met
(not callables on the def) so the registry stays a plain data table --
same reasoning as EnemyDef.spawn_time / biome_id.
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ShopOffer:
    item_id: str
    price: int  # coins; must be > ItemDef.value so buying then selling can't print money


@dataclass(frozen=True)
class NpcDef:
    id: str
    name: str
    color: Tuple[int, int, int]
    dialogue: Tuple[str, ...]
    shop_stock: Tuple[ShopOffer, ...] = ()
    # "always" | "wealth" | "discovered_item" -- see npc_spawner.condition_met
    spawn_condition: str = "always"
    spawn_item_id: Optional[str] = None  # required item id when spawn_condition is "discovered_item"
    # Playable-character idle skin reused by Renderer._draw_npcs. None
    # keeps the old flat humanoid. ninja_frog is the default player skin
    # -- don't point NPCs at it.
    sprite_character_id: Optional[str] = None
