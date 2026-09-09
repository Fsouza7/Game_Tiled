"""Recipe schema: ingredients, result and an optional required station."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class RecipeDef:
    id: str
    name: str
    ingredients: Tuple[Tuple[str, int], ...]  # (item_id, quantity) pairs
    result_item_id: str
    result_quantity: int = 1
    station_tile_id: Optional[int] = None  # None = craftable anywhere by hand
