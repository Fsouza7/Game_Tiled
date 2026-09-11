"""Central, data-driven table of every summon (minion) kind, one per
summon rod tier -- see item_registry.py's summon_rod_wood/summon_rod_iron
(ItemDef.summons_id) and class_registry.py's Summoner class.
"""
from typing import Dict, List

from game.entities.summon_def import SummonDef

_SUMMONS: Dict[str, SummonDef] = {}


def _register(summon_def: SummonDef) -> None:
    if summon_def.id in _SUMMONS:
        raise ValueError(f"Duplicate summon id {summon_def.id}")
    _SUMMONS[summon_def.id] = summon_def


_register(SummonDef(
    id="twig_sprite", name="Twig Sprite",
    damage=7.0, attack_interval_s=0.8, move_speed=5.0,
    width_tiles=0.6, height_tiles=0.6, color=(140, 210, 120),
    attack_range_tiles=1.4, seek_radius_tiles=10.0, follow_distance_tiles=6.0,
))

_register(SummonDef(
    id="iron_guardian", name="Iron Guardian",
    damage=14.0, attack_interval_s=0.7, move_speed=5.5,
    width_tiles=0.8, height_tiles=0.8, color=(180, 180, 190),
    attack_range_tiles=1.6, seek_radius_tiles=12.0, follow_distance_tiles=6.0,
))

_register(SummonDef(
    id="steel_colossus", name="Steel Colossus",
    damage=21.0, attack_interval_s=0.6, move_speed=5.8,
    width_tiles=0.9, height_tiles=0.9, color=(140, 150, 175),
    attack_range_tiles=1.7, seek_radius_tiles=13.0, follow_distance_tiles=6.0,
))

_register(SummonDef(
    id="arcane_familiar", name="Arcane Familiar",
    damage=27.0, attack_interval_s=0.65, move_speed=6.5,
    width_tiles=0.7, height_tiles=0.7, color=(160, 120, 230),
    attack_range_tiles=1.8, seek_radius_tiles=14.0, follow_distance_tiles=6.0,
))

# --- Post-Arcane tier: Voidsteel Rod's summon (see item_registry.py's
# summon_rod_voidsteel) -- the strongest minion in the game. ---

_register(SummonDef(
    id="void_wraith", name="Void Wraith",
    damage=34.0, attack_interval_s=0.65, move_speed=6.0,
    width_tiles=0.9, height_tiles=0.9, color=(90, 30, 140),
    attack_range_tiles=1.8, seek_radius_tiles=13.0, follow_distance_tiles=6.5,
))


def get(summon_id: str) -> SummonDef:
    return _SUMMONS[summon_id]


def all_summons() -> List[SummonDef]:
    return list(_SUMMONS.values())
