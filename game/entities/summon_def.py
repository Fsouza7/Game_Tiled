"""Summon (minion) schema -- see summon_registry.py, summon.py, summon_ai.py.

Mirrors enemy_def.py's split: this is pure data, runtime state lives on
Summon, behavior lives in summon_ai.py.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SummonDef:
    id: str
    name: str
    damage: float
    attack_interval_s: float
    move_speed: float
    width_tiles: float
    height_tiles: float
    color: Tuple[int, int, int]
    attack_range_tiles: float
    seek_radius_tiles: float      # how far it'll fly off to engage an enemy
    follow_distance_tiles: float  # snaps back toward the player past this
