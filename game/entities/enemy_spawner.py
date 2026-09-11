"""Periodically spawns enemies near the player, respecting a population cap
and each enemy's spawn_weight (see EnemyDef). Both the cap and the spawn
cadence depend on where/when the player is (see _current_limits): fewer,
slower spawns in daylight at the surface; more, faster ones at night;
underground is the most dangerous of all, at any hour, since caves are
already dark regardless of the surface day/night cycle (see "How lighting
works" in README).
"""
import random
from typing import List, Optional, Tuple

from game.entities.enemy import Enemy
from game.entities import enemy_registry, difficulty
from game.entities.enemy_def import SpawnTime, AIType
from game.settings import (
    TILE_SIZE, ENEMY_MAX_ALIVE_DAY, ENEMY_MAX_ALIVE_NIGHT, ENEMY_MAX_ALIVE_UNDERGROUND,
    ENEMY_SPAWN_INTERVAL_DAY_S, ENEMY_SPAWN_INTERVAL_NIGHT_S, ENEMY_SPAWN_INTERVAL_UNDERGROUND_S,
    UNDERGROUND_SPAWN_DEPTH_TILES,
    ENEMY_SPAWN_MIN_DISTANCE_TILES, ENEMY_SPAWN_MAX_DISTANCE_TILES,
    ENEMY_DESPAWN_DISTANCE_TILES, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, BEDROCK_ROWS,
    FLYING_SPAWN_HEIGHT_TILES,
)
from game.world.world import World
from game.world.world_generator import biome_at

# How far above/below the player's own depth to search for a valid
# underground spot (a real cave floor for ground mobs, any open tile for
# flyers) -- see _underground_spawn_y_tiles.
UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES = 20


class EnemySpawner:
    def __init__(self):
        self.time_until_next_spawn = ENEMY_SPAWN_INTERVAL_DAY_S

    def update(self, dt: float, world: World, player, enemies: List[Enemy], is_night: bool, day_count: int = 1) -> None:
        self._despawn_far_enemies(player, enemies)

        max_alive, spawn_interval, underground = self._current_limits(world, player, is_night)

        self.time_until_next_spawn -= dt
        if self.time_until_next_spawn > 0.0:
            return
        self.time_until_next_spawn = spawn_interval

        if len(enemies) >= max_alive:
            return

        spawned = self._try_spawn(world, player, is_night, underground, day_count)
        if spawned is not None:
            enemies.append(spawned)

    def _current_limits(self, world: World, player, is_night: bool) -> Tuple[int, float, bool]:
        """(max_alive, spawn_interval_s, underground) for right now.
        Underground overrides day/night entirely -- it only kicks in once
        the player is UNDERGROUND_SPAWN_DEPTH_TILES below the surface, so
        a shallow dip in the terrain doesn't toggle it back and forth."""
        player_tile_x = int(player.center_x // TILE_SIZE)
        player_tile_y = int(player.center_y // TILE_SIZE)
        surface_y = world.surface_height_at(player_tile_x)
        if player_tile_y - surface_y >= UNDERGROUND_SPAWN_DEPTH_TILES:
            return ENEMY_MAX_ALIVE_UNDERGROUND, ENEMY_SPAWN_INTERVAL_UNDERGROUND_S, True
        if is_night:
            return ENEMY_MAX_ALIVE_NIGHT, ENEMY_SPAWN_INTERVAL_NIGHT_S, False
        return ENEMY_MAX_ALIVE_DAY, ENEMY_SPAWN_INTERVAL_DAY_S, False

    def _despawn_far_enemies(self, player, enemies: List[Enemy]) -> None:
        for enemy in enemies:
            distance_tiles = abs(enemy.center_x - player.center_x) / TILE_SIZE
            if distance_tiles > ENEMY_DESPAWN_DISTANCE_TILES:
                enemy.alive = False

    def _try_spawn(self, world: World, player, is_night: bool, underground: bool, day_count: int = 1):
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

        if underground:
            spawn_y = _underground_spawn_y_tiles(world, spawn_x, player.center_y / TILE_SIZE, enemy_def)
            if spawn_y is None:
                return None  # nothing suitable nearby -- skip this attempt rather than fall back to the surface
        else:
            spawn_y = _spawn_y_tiles(world, spawn_x, enemy_def)

        # Day-based difficulty scaling (see game/entities/difficulty.py) --
        # baked into the instance at spawn time, so a mob spawned later in
        # the playthrough is tougher than one spawned on day 1, without
        # retroactively buffing anything already alive.
        return Enemy(
            enemy_def, spawn_x * TILE_SIZE, spawn_y * TILE_SIZE,
            health_multiplier=difficulty.health_multiplier(day_count),
            damage_multiplier=difficulty.damage_multiplier(day_count),
        )

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


def _underground_spawn_y_tiles(world: World, spawn_x: int, player_tile_y: float, enemy_def) -> Optional[int]:
    """Scans vertically near the player's own depth in column spawn_x for
    a valid cave spot: a ground mob needs a real cave floor (solid tile
    directly beneath an open tile, open tile above that too); a flyer
    just needs one open tile, since it ignores gravity/collision entirely
    (see enemy_ai._update_fly). Tried in random order across the search
    band rather than top-down, so repeated spawns near the same column
    don't all cluster at the first opening found. Returns None if nothing
    suitable turns up -- the caller skips this spawn attempt instead of
    falling back to the surface, so "dangerous depths" never silently
    reads as "surface as usual"."""
    center_y = int(player_tile_y)
    min_y = max(1, center_y - UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES)
    max_y = min(WORLD_HEIGHT_TILES - BEDROCK_ROWS - 2, center_y + UNDERGROUND_SPAWN_SEARCH_RADIUS_TILES)
    candidates = list(range(min_y, max_y + 1))
    random.shuffle(candidates)
    for y in candidates:
        if world.is_solid(spawn_x, y):
            continue
        if enemy_def.ai_type == AIType.FLY:
            return y
        if world.is_solid(spawn_x, y + 1) and not world.is_solid(spawn_x, y - 1):
            return y
    return None
