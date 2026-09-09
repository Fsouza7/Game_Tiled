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
    damage=2.0, attack_interval_s=1.2, move_speed=4.5,
    width_tiles=0.6, height_tiles=0.6, color=(140, 210, 120),
    attack_range_tiles=1.0, seek_radius_tiles=8.0, follow_distance_tiles=6.0,
))

_register(SummonDef(
    id="iron_guardian", name="Iron Guardian",
    damage=7.0, attack_interval_s=1.0, move_speed=5.5,
    width_tiles=0.8, height_tiles=0.8, color=(180, 180, 190),
    attack_range_tiles=1.2, seek_radius_tiles=10.0, follow_distance_tiles=6.0,
))


def get(summon_id: str) -> SummonDef:
    return _SUMMONS[summon_id]


def all_summons() -> List[SummonDef]:
    return list(_SUMMONS.values())
