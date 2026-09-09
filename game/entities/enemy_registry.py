"""Central, data-driven table of every enemy type. Adding an enemy means
adding one entry here (see README "Como criar um inimigo").
"""
from typing import Dict, List

from game.entities.enemy_def import EnemyDef, AIType, SpawnTime
from game.world.biome_registry import DESERT_ID

_ENEMIES: Dict[str, EnemyDef] = {}


def _register(enemy: EnemyDef) -> None:
    if enemy.id in _ENEMIES:
        raise ValueError(f"Duplicate enemy id {enemy.id}")
    _ENEMIES[enemy.id] = enemy


_register(EnemyDef(
    id="slime", name="Slime",
    ai_type=AIType.HOP,
    max_health=20.0, contact_damage=8.0, move_speed=5.0,
    width_tiles=0.8, height_tiles=0.6, color=(90, 200, 110),
    spawn_weight=0.5,
    drop_item_id="slime_gel", drop_chance=0.8, drop_min=1, drop_max=2,
))

_register(EnemyDef(
    id="crawler", name="Crawler",
    ai_type=AIType.WALK,
    max_health=35.0, contact_damage=12.0, move_speed=3.5,
    width_tiles=0.9, height_tiles=0.9, color=(150, 70, 60),
    spawn_weight=0.3,
    drop_item_id="coal", drop_chance=0.5, drop_min=1, drop_max=1,
))

_register(EnemyDef(
    id="duskwing", name="Duskwing",
    ai_type=AIType.FLY,
    max_health=16.0, contact_damage=7.0, move_speed=5.5,
    width_tiles=0.8, height_tiles=0.6, color=(120, 90, 170),
    spawn_weight=0.35, spawn_time=SpawnTime.NIGHT,
    drop_item_id="feather", drop_chance=0.6, drop_min=1, drop_max=2,
))

_register(EnemyDef(
    id="scorpion", name="Scorpion",
    ai_type=AIType.WALK,
    max_health=28.0, contact_damage=14.0, move_speed=4.5,
    width_tiles=0.9, height_tiles=0.6, color=(200, 150, 60),
    spawn_weight=0.4, biome_id=DESERT_ID,
    drop_item_id="cactus_fiber", drop_chance=0.5, drop_min=1, drop_max=2,
))


def get(enemy_id: str) -> EnemyDef:
    return _ENEMIES[enemy_id]


def all_enemies() -> List[EnemyDef]:
    return list(_ENEMIES.values())
