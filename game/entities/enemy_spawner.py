"""Periodically spawns enemies near the player, respecting a population cap
and each enemy's spawn_weight (see EnemyDef)."""
import random
from typing import List, Optional

from game.entities.enemy import Enemy
from game.entities import enemy_registry
from game.entities.enemy_def import SpawnTime, AIType
from game.settings import (
    TILE_SIZE, ENEMY_MAX_ALIVE, ENEMY_SPAWN_INTERVAL_S,
    ENEMY_SPAWN_MIN_DISTANCE_TILES, ENEMY_SPAWN_MAX_DISTANCE_TILES,
    ENEMY_DESPAWN_DISTANCE_TILES, WORLD_WIDTH_TILES,
    FLYING_SPAWN_HEIGHT_TILES,
)
from game.world.world import World
from game.world.world_generator import biome_at


class EnemySpawner:
    def __init__(self):
        self.time_until_next_spawn = ENEMY_SPAWN_INTERVAL_S

    def update(self, dt: float, world: World, player, enemies: List[Enemy], is_night: bool) -> None:
        self._despawn_far_enemies(player, enemies)

        self.time_until_next_spawn -= dt
        if self.time_until_next_spawn > 0.0:
            return
        self.time_until_next_spawn = ENEMY_SPAWN_INTERVAL_S

        if len(enemies) >= ENEMY_MAX_ALIVE:
            return

        spawned = self._try_spawn(world, player, is_night)
        if spawned is not None:
            enemies.append(spawned)

    def _despawn_far_enemies(self, player, enemies: List[Enemy]) -> None:
        for enemy in enemies:
            distance_tiles = abs(enemy.center_x - player.center_x) / TILE_SIZE
            if distance_tiles > ENEMY_DESPAWN_DISTANCE_TILES:
                enemy.alive = False

    def _try_spawn(self, world: World, player, is_night: bool):
        player_tile_x = int(player.center_x // TILE_SIZE)
        direction = random.choice((-1, 1))
        distance = random.randint(ENEMY_SPAWN_MIN_DISTANCE_TILES, ENEMY_SPAWN_MAX_DISTANCE_TILES)
        spawn_x = player_tile_x + direction * distance
        if not (0 <= spawn_x < WORLD_WIDTH_TILES):
            return None

        biome_id = biome_at(world.seed, spawn_x).id
        enemy_def = self._pick_weighted_enemy(is_night, biome_id)
        if enemy_def is None:
            return None

        spawn_y = _spawn_y_tiles(world, spawn_x, enemy_def)
        return Enemy(enemy_def, spawn_x * TILE_SIZE, spawn_y * TILE_SIZE)

    def _pick_weighted_enemy(self, is_night: bool, biome_id: Optional[str] = None):
        eligible = [
            e for e in enemy_registry.all_enemies()
            # Bosses are never randomly spawned -- only GameApp.try_summon_boss
            # constructs one, from a boss idol (see enemy_registry.py's
            # slime_king entry, whose spawn_weight=0.0 already makes this
            # redundant -- kept explicit so a future boss can't be picked
            # here just by forgetting to zero its spawn_weight).
            if e.ai_type != AIType.BOSS
            and self._matches_time(e.spawn_time, is_night) and self._matches_biome(e.biome_id, biome_id)
        ]
        if not eligible:
            return None
        weights = [e.spawn_weight for e in eligible]
        return random.choices(eligible, weights=weights, k=1)[0]

    @staticmethod
    def _matches_time(spawn_time: SpawnTime, is_night: bool) -> bool:
        if spawn_time == SpawnTime.ANY:
            return True
        return (spawn_time == SpawnTime.NIGHT) == is_night

    @staticmethod
    def _matches_biome(enemy_biome_id: Optional[str], current_biome_id: Optional[str]) -> bool:
        return enemy_biome_id is None or enemy_biome_id == current_biome_id


def _spawn_y_tiles(world: World, spawn_x: int, enemy_def) -> int:
    """Ground mobs sit on the grass; flyers hover above it (and above trees)."""
    surface_y = world.surface_spawn_y(spawn_x) + 1  # grass row
    spawn_y = surface_y - 1  # just above the ground
    if enemy_def.ai_type != AIType.FLY:
        return spawn_y
    spawn_y -= FLYING_SPAWN_HEIGHT_TILES
    while spawn_y > 1 and world.is_solid(spawn_x, spawn_y):
        spawn_y -= 1
    return spawn_y
