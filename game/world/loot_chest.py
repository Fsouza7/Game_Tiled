"""Random loot for world-generated Chest tiles (found inside structures --
Houses, Ruins, Underground Rooms). Opened the same way as the Personal
Chest (walk up, press T) but each Chest is its own one-time roll instead
of a player-bound shared stash.

The roll is a pure function of (seed, tile position) -- same determinism
guarantee trees/ore/structures already rely on -- so a given Chest always
re-derives the same starting contents the first time it's opened, whether
that's on first discovery or a hundred sessions later. World.chest_loot
caches the rolled Inventory per position so items taken out stay taken;
see save_system for how a touched chest's remaining contents persist.
"""
import random
from typing import List, Tuple

from game.inventory.inventory import Inventory
from game.settings import LOOT_CHEST_SLOTS, LOOT_CHEST_MIN_ROLLS, LOOT_CHEST_MAX_ROLLS

# (item_id, min_qty, max_qty, weight) -- each rolled chest draws a handful
# of *different* entries (no replacement), weighted so bars/gems are rarer
# than coins/wood/torches.
LOOT_POOL: List[Tuple[str, int, int, float]] = [
    ("iron_bar", 1, 3, 3.0),
    ("topaz", 1, 2, 1.0),
    ("sapphire", 1, 2, 1.0),
    ("emerald", 1, 2, 1.0),
    ("iron_pickaxe", 1, 1, 1.5),
    ("wood_sword", 1, 1, 1.5),
    ("wood_helmet", 1, 1, 1.5),
    ("coin", 5, 20, 3.0),
    ("wood", 5, 15, 2.0),
    ("torch", 2, 6, 2.0),
]


def _position_rng(seed: int, tile_x: int, tile_y: int) -> random.Random:
    mixed = (seed * 668265263 + tile_x * 374761393 + tile_y * 2246822519) & 0xFFFFFFFF
    return random.Random(mixed ^ 0xC4E57)


def roll_chest_loot(seed: int, tile_x: int, tile_y: int) -> Inventory:
    rng = _position_rng(seed, tile_x, tile_y)
    inventory = Inventory(size=LOOT_CHEST_SLOTS)

    pool = list(LOOT_POOL)
    weights = [entry[3] for entry in pool]
    roll_count = min(rng.randint(LOOT_CHEST_MIN_ROLLS, LOOT_CHEST_MAX_ROLLS), len(pool))

    for _ in range(roll_count):
        chosen = rng.choices(range(len(pool)), weights=weights, k=1)[0]
        item_id, min_qty, max_qty, _ = pool.pop(chosen)
        weights.pop(chosen)
        inventory.add_item(item_id, rng.randint(min_qty, max_qty))

    return inventory
