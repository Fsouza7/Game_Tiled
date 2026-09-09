"""Central, data-driven table of every biome. Adding a biome means adding
one entry here (see README "Como criar um bioma") plus, if it needs unique
vegetation/decoration, a small hook in world_generator.py.
"""
from typing import Dict, List

from game.world.biome import BiomeDef
from game.world import tile_registry

FOREST_ID = "forest"
DESERT_ID = "desert"
SNOW_ID = "snow"
JUNGLE_ID = "jungle"

_BIOMES: Dict[str, BiomeDef] = {}


def _register(biome: BiomeDef) -> None:
    if biome.id in _BIOMES:
        raise ValueError(f"Duplicate biome id {biome.id}")
    _BIOMES[biome.id] = biome


_register(BiomeDef(
    id=FOREST_ID, name="Forest",
    surface_tile_id=tile_registry.GRASS_ID, subsurface_tile_id=tile_registry.DIRT_ID,
    zone_weight=0.4,
    underground_tile_id=tile_registry.STONE_ID,
))

_register(BiomeDef(
    id=DESERT_ID, name="Desert",
    surface_tile_id=tile_registry.SAND_ID, subsurface_tile_id=tile_registry.SANDSTONE_ID,
    zone_weight=0.2,
    underground_tile_id=tile_registry.DESERT_STONE_ID,
    exclusive_ore_tile_id=tile_registry.TOPAZ_ORE_ID, exclusive_ore_chance=0.015,
))

_register(BiomeDef(
    id=SNOW_ID, name="Snow",
    surface_tile_id=tile_registry.SNOW_BLOCK_ID, subsurface_tile_id=tile_registry.FROZEN_DIRT_ID,
    zone_weight=0.2,
    underground_tile_id=tile_registry.SNOW_STONE_ID,
    exclusive_ore_tile_id=tile_registry.SAPPHIRE_ORE_ID, exclusive_ore_chance=0.015,
))

_register(BiomeDef(
    id=JUNGLE_ID, name="Jungle",
    surface_tile_id=tile_registry.JUNGLE_GRASS_ID, subsurface_tile_id=tile_registry.MUD_ID,
    zone_weight=0.2,
    underground_tile_id=tile_registry.JUNGLE_STONE_ID,
    exclusive_ore_tile_id=tile_registry.EMERALD_ORE_ID, exclusive_ore_chance=0.015,
))


def get(biome_id: str) -> BiomeDef:
    return _BIOMES[biome_id]


def all_biomes() -> List[BiomeDef]:
    return list(_BIOMES.values())
