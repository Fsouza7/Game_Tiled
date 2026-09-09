"""NPC spawn conditions and house assignment.

NPCs occupy world-generated Houses (Phase 7) when one is close enough,
falling back to a standing position on the surface near world-center
spawn so the Guide is always findable even if the nearest House rolled
far away. Assignment is a pure function of (seed, npc registry order):
the same NPC always claims the same home for a given seed, independent
of the order conditions unlock.

Once an NPC has appeared they stay, even if the condition later fails
(e.g. the player sells enough that wealth drops below the Merchant
threshold) -- flickering in and out would feel like a bug.

NPCs themselves are not persisted: on load, conditions are re-derived
from player state and they reappear at the same homes. Same
transient/regenerable treatment enemies already get.
"""
from typing import List, Optional, Tuple

from game.npcs.npc import Npc
from game.npcs.npc_def import NpcDef
from game.npcs import npc_registry, shop
from game.settings import (
    TILE_SIZE, WORLD_WIDTH_TILES, STRUCTURE_SLOT_WIDTH_TILES,
    NPC_INTERACT_RANGE_TILES, NPC_GUIDE_MAX_HOUSE_DISTANCE_TILES,
    NPC_HOME_SEARCH_MAX_DISTANCE_TILES, NPC_MERCHANT_MIN_WEALTH,
    NPC_WIDTH_TILES, NPC_HEIGHT_TILES,
)
from game.world.tile_registry import AIR_ID
from game.world import structures
from game.world.structures import HOUSE


def condition_met(npc_def: NpcDef, player) -> bool:
    if npc_def.spawn_condition == "always":
        return True
    if npc_def.spawn_condition == "wealth":
        return shop.wealth(player.inventory) >= NPC_MERCHANT_MIN_WEALTH
    if npc_def.spawn_condition == "discovered_item":
        return npc_def.spawn_item_id in player.discovered_item_ids
    raise ValueError(f"Unknown spawn condition {npc_def.spawn_condition!r}")


def iter_houses_nearest_first(seed: int) -> List[structures.StructureInstance]:
    """Every House in the world, nearest to world-center spawn first.
    Cheap: structure_for_slot is a pure function of (seed, slot_index),
    ~100 slots, same cost as a one-time scan at run start."""
    spawn_x = WORLD_WIDTH_TILES // 2
    slot_count = WORLD_WIDTH_TILES // STRUCTURE_SLOT_WIDTH_TILES
    houses = []
    for slot_index in range(slot_count):
        instance = structures.structure_for_slot(seed, slot_index)
        if instance is not None and instance.kind == HOUSE:
            houses.append(instance)
    houses.sort(key=lambda h: abs(h.anchor_x - spawn_x))
    return houses


def _standing_position(floor_tile_x: int, floor_tile_y: int) -> Tuple[float, float]:
    """Top-left of an NPC standing on the top of the floor tile at
    (floor_tile_x, floor_tile_y). NPCs have no physics, so this has to
    put their feet exactly on the floor rather than overlapping it and
    waiting for gravity to settle them (that's what Player spawn does)."""
    width = NPC_WIDTH_TILES * TILE_SIZE
    height = NPC_HEIGHT_TILES * TILE_SIZE
    x = floor_tile_x * TILE_SIZE + (TILE_SIZE - width) / 2
    y = floor_tile_y * TILE_SIZE - height
    return x, y


def position_in_house(instance: structures.StructureInstance) -> Tuple[float, float]:
    """Center column of the house, standing on the floor (dy=0 of the
    blueprint -- see structures._house_blueprint)."""
    return _standing_position(instance.anchor_x, instance.anchor_y)


def fallback_surface_position(world, offset_tiles: int) -> Tuple[float, float]:
    """A standing spot on the surface near spawn, offset by `offset_tiles`.
    Walks outward from that column if the tile above the surface isn't
    air (a tree trunk, crate, etc.) so the NPC isn't spawned inside a
    solid block."""
    spawn_x = WORLD_WIDTH_TILES // 2
    preferred = spawn_x + offset_tiles
    step = 1 if offset_tiles >= 0 else -1
    tile_x = preferred
    for _ in range(40):
        tile_x = max(0, min(WORLD_WIDTH_TILES - 1, tile_x))
        floor_y = world.surface_height_at(tile_x)
        if world.get_tile(tile_x, floor_y - 1) == AIR_ID:
            return _standing_position(tile_x, floor_y)
        tile_x += step
    floor_y = world.surface_height_at(preferred)
    return _standing_position(preferred, floor_y)


def homes_for_world(world) -> List[Tuple[float, float]]:
    """One home (x_px, y_px) per registered NPC, in registry order.
    Guide claims the nearest House only if it's within
    NPC_GUIDE_MAX_HOUSE_DISTANCE_TILES of spawn (otherwise a surface
    fallback a few tiles left of spawn, so they're actually findable).
    Later NPCs take the next unused nearby House, or further fallbacks.
    """
    spawn_x = WORLD_WIDTH_TILES // 2
    houses = [
        h for h in iter_houses_nearest_first(world.seed)
        if abs(h.anchor_x - spawn_x) <= NPC_HOME_SEARCH_MAX_DISTANCE_TILES
    ]
    npc_count = len(npc_registry.all_npcs())
    # Offsets keep fallbacks from stacking on the player (offset 0) and
    # each other. Guide gets -6 so they're the first thing you see walking
    # left; others go right/further left.
    fallback_offsets = (-6, 8, -14, 16, -22)
    homes: List[Tuple[float, float]] = []
    used_houses = 0
    for i in range(npc_count):
        if i == 0:
            if houses and abs(houses[0].anchor_x - spawn_x) <= NPC_GUIDE_MAX_HOUSE_DISTANCE_TILES:
                homes.append(position_in_house(houses[0]))
                used_houses = 1
            else:
                homes.append(fallback_surface_position(world, fallback_offsets[0]))
            continue
        if used_houses < len(houses):
            homes.append(position_in_house(houses[used_houses]))
            used_houses += 1
        else:
            offset = fallback_offsets[min(i, len(fallback_offsets) - 1)]
            homes.append(fallback_surface_position(world, offset))
    return homes


def nearest_in_range(player, npcs: List[Npc]) -> Optional[Npc]:
    """Closest NPC whose center is within NPC_INTERACT_RANGE_TILES of
    the player's, or None. Used by the T-to-talk key and the nameplate prompt."""
    best = None
    best_d_sq = (NPC_INTERACT_RANGE_TILES * TILE_SIZE) ** 2
    for npc in npcs:
        dx = npc.center_x - player.center_x
        dy = npc.center_y - player.center_y
        d_sq = dx * dx + dy * dy
        if d_sq <= best_d_sq:
            best = npc
            best_d_sq = d_sq
    return best


class NpcSpawner:
    """Keeps `npcs` in sync with whichever spawn conditions currently hold.

    `quiet_until_synced` suppresses the 'has arrived' toast for the next
    update -- used on load so a Merchant who already qualified doesn't
    re-announce themselves. First frame of a new run only spawns the
    Guide (always), who we never toast anyway.
    """

    def __init__(self):
        self._homes = None
        self.quiet_until_synced = False

    def update(self, world, player, npcs: List[Npc]) -> List[str]:
        """Appends any newly-qualified NPCs onto `npcs`. Returns their
        ids (for a toast) -- empty when quiet_until_synced."""
        if self._homes is None:
            self._homes = homes_for_world(world)

        present = {npc.npc_def.id for npc in npcs}
        newly = []
        for i, npc_def in enumerate(npc_registry.all_npcs()):
            if npc_def.id in present:
                continue
            if not condition_met(npc_def, player):
                continue
            x, y = self._homes[i]
            npcs.append(Npc(npc_def, x, y))
            newly.append(npc_def.id)

        if self.quiet_until_synced:
            self.quiet_until_synced = False
            return []
        return newly
