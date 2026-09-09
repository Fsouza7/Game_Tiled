"""Biome schema: what ground a horizontal stretch of the world is made of."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BiomeDef:
    id: str
    name: str
    surface_tile_id: int
    subsurface_tile_id: int
    zone_weight: float  # relative chance when picking a non-forest zone
    underground_tile_id: int  # deep "stone" filler below the dirt layer
    exclusive_ore_tile_id: Optional[int] = None  # None = no biome-exclusive ore
    exclusive_ore_chance: float = 0.0  # roll chance, on top of universal coal/iron
