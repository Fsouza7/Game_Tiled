"""Enemy schema: the data every enemy type is built from."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class AIType(Enum):
    WALK = "walk"    # ground patrol, turns at walls/ledges, chases on sight
    HOP = "hop"      # periodic jumps, ground-bound (slime-style)
    FLY = "fly"      # ignores gravity, hovers/bobs, chases on sight


class SpawnTime(Enum):
    ANY = "any"      # spawns regardless of day/night
    DAY = "day"      # only while WorldClock.is_night is False
    NIGHT = "night"  # only while WorldClock.is_night is True


@dataclass(frozen=True)
class EnemyDef:
    id: str
    name: str
    ai_type: AIType
    max_health: float
    contact_damage: float
    move_speed: float  # px/frame, same scale as PLAYER_MOVE_SPEED (not tiles/sec)
    width_tiles: float
    height_tiles: float
    color: Tuple[int, int, int]
    spawn_weight: float  # relative chance among all enemies when spawning
    spawn_time: SpawnTime = SpawnTime.ANY
    biome_id: Optional[str] = None  # None = spawns in any biome; else a biome_registry id
    drop_item_id: Optional[str] = None
    drop_chance: float = 0.0
    drop_min: int = 1
    drop_max: int = 1
