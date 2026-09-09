"""A vertical slice of the world: CHUNK_WIDTH columns, full world height.

Column-based chunking keeps Phase 1 simple (one axis to load/unload) while
still giving the perf properties the project needs: only chunks near the
player exist in memory, and only chunks on screen get drawn.
"""
from typing import List

from game.settings import CHUNK_WIDTH, WORLD_HEIGHT_TILES
from game.world.tile_registry import AIR_ID
from game.world.hazard_feature import HazardAnchor


class Chunk:
    def __init__(self, chunk_x: int):
        self.chunk_x = chunk_x
        # tiles[local_x][y] -- local_x in [0, CHUNK_WIDTH)
        self.tiles: List[List[int]] = [
            [AIR_ID] * WORLD_HEIGHT_TILES for _ in range(CHUNK_WIDTH)
        ]
        # True once a tile in this chunk differs from the procedural
        # baseline -- SaveSystem (Phase 1 does not persist worlds yet) will
        # use this to avoid writing untouched chunks to disk.
        self.dirty = False
        # Moving hazard anchors (Saw/Rock Head/Spike Head) rolled once at
        # generation time -- see game/world/hazard_feature.py. Regenerated
        # identically if this chunk is unloaded and reloaded (pure function
        # of seed + column, like everything else here), so it needs no
        # persistence of its own.
        self.hazards: List[HazardAnchor] = []

    def get_tile(self, local_x: int, y: int) -> int:
        return self.tiles[local_x][y]

    def set_tile(self, local_x: int, y: int, tile_id: int) -> None:
        self.tiles[local_x][y] = tile_id
        self.dirty = True
