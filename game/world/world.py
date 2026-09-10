"""Owns all chunks and is the single source of truth for tile state.

Chunks are generated lazily (on first access) and unloaded when far from the
player, so memory and generation cost scale with what has actually been
explored, not with WORLD_WIDTH_TILES.
"""
import logging
import random
from typing import Dict, Iterator, Optional, Tuple

from game.settings import (
    CHUNK_WIDTH, TILE_SIZE, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES,
    CHUNK_LOAD_RADIUS, CHUNK_UNLOAD_RADIUS,
    FALLING_PLATFORM_TRIGGER_S, FALLING_PLATFORM_RESPAWN_S,
)
from game.world.chunk import Chunk
from game.world.world_generator import generate_column, generate_hazard_anchor
from game.world import tile_registry
from game.world.tile_registry import AIR_ID
from game.world.hazard_feature import HazardAnchor
from game.world import loot_chest
from game.world import exploration
from game.inventory.inventory import Inventory

logger = logging.getLogger(__name__)


class World:
    def __init__(self, seed: int):
        self.seed = seed
        self.chunks: Dict[int, Chunk] = {}
        # Total real seconds this world has been running -- drives the
        # moving hazards' sine oscillation (see hazard_feature.py) and
        # nothing else, so it doesn't need to be saved/restored.
        self.elapsed_s = 0.0
        # Falling Platform state: at most one tile is ever "being stood on"
        # at a time (single player), so this is scalar rather than a dict
        # keyed by every platform tile in the world. See notify_standing_on.
        self._crumble_stand_pos: Optional[Tuple[int, int]] = None
        self._crumble_stand_time = 0.0
        self._crumble_pending: Dict[Tuple[int, int], float] = {}
        # World-generated loot Chests (see game/world/loot_chest.py): only
        # populated for chests that have actually been opened at least
        # once -- an untouched chest re-derives the same roll on demand,
        # so there's nothing to store for it ahead of time.
        self.chest_loot: Dict[Tuple[int, int], Inventory] = {}
        # Fog-of-war Map data (see game/world/exploration.py): cell ->
        # its sampled RGB color, populated as the player walks around.
        self.explored_cells: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
        # Edits belonging to a chunk that's since been unloaded (see
        # _unload_far_chunks) -- chunk_x -> its diff against the
        # procedural baseline, in the same (local_x, y, tile_id) shape
        # save_system uses. Without this, a chunk's edits (mining,
        # building, a placed Furnace/Personal Chest/Torch/Checkpoint)
        # vanished the moment the player wandered CHUNK_UNLOAD_RADIUS
        # chunks away -- not just from live memory, but from any save
        # made afterward too, since serialize() only ever looked at
        # world.chunks, which no longer had the chunk in it at all.
        self._unloaded_chunk_diffs: Dict[int, list] = {}

    def chunk_diff(self, chunk_x: int, chunk: Chunk) -> list:
        """(local_x, y, tile_id) triples for every tile in this chunk that
        differs from the procedural baseline -- generate_column is a cheap
        pure function of (seed, x), so recomputing it here to diff against
        is fine, the same cost already paid every chunk load/unload.
        Shared by save_system.serialize (for currently-loaded chunks) and
        _unload_far_chunks (to preserve a chunk's edits past unloading)."""
        diff = []
        base_x = chunk_x * CHUNK_WIDTH
        for local_x in range(CHUNK_WIDTH):
            world_x = base_x + local_x
            if world_x >= WORLD_WIDTH_TILES:
                break
            baseline = generate_column(self.seed, world_x)
            live = chunk.tiles[local_x]
            for y, tile_id in enumerate(live):
                if tile_id != baseline[y]:
                    diff.append((local_x, y, tile_id))
        return diff

    def reveal_map_around(self, center_x_px: float, center_y_px: float) -> None:
        exploration.reveal_around(self, center_x_px, center_y_px)

    def get_chest_inventory(self, tile_x: int, tile_y: int) -> Inventory:
        """Returns the given Chest tile's loot -- rolled once, the first
        time this is called for that position, then the same Inventory
        instance on every later call, so items taken out stay taken."""
        key = (tile_x, tile_y)
        inventory = self.chest_loot.get(key)
        if inventory is None:
            inventory = loot_chest.roll_chest_loot(self.seed, tile_x, tile_y)
            self.chest_loot[key] = inventory
        return inventory

    def update(self, dt: float) -> None:
        self.elapsed_s += dt
        self._update_crumble_respawns(dt)

    # --- bounds ---
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < WORLD_WIDTH_TILES and 0 <= y < WORLD_HEIGHT_TILES

    # --- chunk lifecycle ---
    def chunk_index_for(self, x: int) -> int:
        return x // CHUNK_WIDTH

    def get_or_create_chunk(self, chunk_x: int) -> Chunk:
        chunk = self.chunks.get(chunk_x)
        if chunk is None:
            chunk = Chunk(chunk_x)
            base_x = chunk_x * CHUNK_WIDTH
            for local_x in range(CHUNK_WIDTH):
                world_x = base_x + local_x
                if world_x >= WORLD_WIDTH_TILES:
                    break
                chunk.tiles[local_x] = generate_column(self.seed, world_x)
                anchor = generate_hazard_anchor(self.seed, world_x)
                if anchor is not None:
                    chunk.hazards.append(anchor)
            # Re-apply this chunk's own past edits, if it's been unloaded
            # and regenerated before (see _unload_far_chunks) -- otherwise
            # a player wandering back to a spot they'd already built on
            # would find their edits silently reverted to the raw baseline.
            diff = self._unloaded_chunk_diffs.pop(chunk_x, None)
            if diff is not None:
                for local_x, y, tile_id in diff:
                    chunk.tiles[local_x][y] = tile_id
                chunk.dirty = True
            self.chunks[chunk_x] = chunk
            logger.debug("Generated chunk %d", chunk_x)
        return chunk

    def ensure_chunks_around(self, world_x_px: float) -> None:
        """world_x_px is a pixel-space x coordinate (e.g. player.center_x)."""
        tile_x = int(world_x_px) // TILE_SIZE
        center = self.chunk_index_for(tile_x)
        for cx in range(center - CHUNK_LOAD_RADIUS, center + CHUNK_LOAD_RADIUS + 1):
            if 0 <= cx * CHUNK_WIDTH < WORLD_WIDTH_TILES:
                self.get_or_create_chunk(cx)
        self._unload_far_chunks(center)

    def _unload_far_chunks(self, center_chunk_x: int) -> None:
        to_unload = [
            cx for cx in self.chunks
            if abs(cx - center_chunk_x) > CHUNK_UNLOAD_RADIUS
        ]
        for cx in to_unload:
            chunk = self.chunks[cx]
            if chunk.dirty:
                # Preserve the edits past this unload -- see
                # _unloaded_chunk_diffs' docstring in __init__.
                self._unloaded_chunk_diffs[cx] = self.chunk_diff(cx, chunk)
            del self.chunks[cx]

    # --- tile access ---
    def get_tile(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            return AIR_ID
        chunk = self.get_or_create_chunk(self.chunk_index_for(x))
        return chunk.get_tile(x % CHUNK_WIDTH, y)

    def is_solid(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return True  # treat outside-world as solid so nothing falls out
        return tile_registry.get(self.get_tile(x, y)).solid

    def surface_height_at(self, x: int) -> int:
        from game.world.world_generator import surface_height
        return surface_height(self.seed, x)

    def surface_spawn_y(self, x: int) -> int:
        return self.surface_height_at(x) - 1  # one tile above the grass

    # --- mutation ---
    def try_break_tile(self, x: int, y: int) -> Optional[str]:
        """Removes the tile at (x, y) if breakable and returns its drop id."""
        if not self.in_bounds(x, y):
            return None
        tile_def = tile_registry.get(self.get_tile(x, y))
        if not tile_def.can_break:
            return None
        chunk = self.get_or_create_chunk(self.chunk_index_for(x))
        chunk.set_tile(x % CHUNK_WIDTH, y, AIR_ID)
        if tile_def.drop_pool:
            return random.choice(tile_def.drop_pool)
        return tile_def.drop_item_id

    def try_place_tile(self, x: int, y: int, tile_id: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        if self.get_tile(x, y) != AIR_ID:
            return False
        tile_def = tile_registry.get(tile_id)
        if not tile_def.can_place:
            return False
        has_adjacent_support = any(
            self.get_tile(nx, ny) != AIR_ID
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
            if self.in_bounds(nx, ny)
        )
        if not has_adjacent_support:
            return False
        chunk = self.get_or_create_chunk(self.chunk_index_for(x))
        chunk.set_tile(x % CHUNK_WIDTH, y, tile_id)
        return True

    # --- moving hazards (Saw/Rock Head/Spike Head, see hazard_feature.py) ---
    def iter_hazard_anchors(self) -> Iterator[HazardAnchor]:
        """Only currently-loaded chunks are scanned -- bounded cost
        regardless of world size, same principle as lighting/rendering."""
        for chunk in self.chunks.values():
            yield from chunk.hazards

    # --- Falling Platform (see tile_registry.CRUMBLE_PLATFORM_ID) ---
    @property
    def crumbling_tile_pos(self) -> Optional[Tuple[int, int]]:
        """The (x, y) of the platform currently being stood on, mid-countdown
        -- the renderer uses this to show the shake animation."""
        return self._crumble_stand_pos

    def notify_standing_on(self, tile_x: int, tile_y: int, dt: float) -> None:
        """Call once per frame with the tile directly beneath the player's
        feet while grounded. Crumbles a Falling Platform tile after
        FALLING_PLATFORM_TRIGGER_S of continuous standing; standing on
        anything else (or leaving this tile) resets the timer."""
        if self.get_tile(tile_x, tile_y) != tile_registry.CRUMBLE_PLATFORM_ID:
            self._crumble_stand_pos = None
            return

        pos = (tile_x, tile_y)
        if self._crumble_stand_pos != pos:
            self._crumble_stand_pos = pos
            self._crumble_stand_time = 0.0
        self._crumble_stand_time += dt

        if self._crumble_stand_time >= FALLING_PLATFORM_TRIGGER_S:
            chunk = self.get_or_create_chunk(self.chunk_index_for(tile_x))
            chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, AIR_ID)
            self._crumble_pending[pos] = FALLING_PLATFORM_RESPAWN_S
            self._crumble_stand_pos = None

    def _update_crumble_respawns(self, dt: float) -> None:
        ready = []
        for pos, remaining in self._crumble_pending.items():
            remaining -= dt
            if remaining <= 0.0:
                ready.append(pos)
            else:
                self._crumble_pending[pos] = remaining
        for pos in ready:
            del self._crumble_pending[pos]
            tile_x, tile_y = pos
            if self.get_tile(tile_x, tile_y) == AIR_ID:  # don't clobber a player-placed block
                chunk = self.get_or_create_chunk(self.chunk_index_for(tile_x))
                chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, tile_registry.CRUMBLE_PLATFORM_ID)
