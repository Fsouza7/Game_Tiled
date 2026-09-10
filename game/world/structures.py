"""Procedurally generated structures: House, Ruins, Underground Room.

Same determinism contract as everything else in world generation (see
world_generator.py's module docstring): every structure is a pure function
of (seed, slot_index), where a slot is a coarse column range -- the exact
same pattern trees use (world_generator._tree_center_for_slot /
_nearest_tree_center), just at a much wider slot width since structures are
rarer and bigger. Any column can independently re-derive which slot it
belongs to and what (if anything) that slot contains, with no dependency
on generation order -- required for lazy, out-of-order chunk loading.

Each structure is a hand-built blueprint: a `dx -> {dy: tile_id}` dict
relative to an anchor position (dy=0 is the anchor row). `place_structures`
overlays a column's slice of any nearby structure's blueprint onto that
column -- called last in world_generator.generate_column, so a structure's
carve/overwrite always wins over whatever natural terrain/hazard would
otherwise be there (same last-applied-wins layering already used for
decoration -> cave hazards -> fan shafts).

Tower is deliberately not implemented: the game has no ladder/climbing
mechanic (only single + double jump), so a tall vertical structure's loot
would be unreachable. See TODO.md/README for this and other known gaps.
"""
import random
from typing import Dict, NamedTuple, Optional

from game.settings import (
    STRUCTURE_SLOT_WIDTH_TILES, STRUCTURE_SPAWN_CHANCE_PER_SLOT, STRUCTURE_MARGIN_TILES,
    STRUCTURE_MAX_TERRAIN_VARIANCE_TILES, UNDERGROUND_ROOM_MIN_DEPTH_BELOW_SURFACE,
    RUINS_WALL_COLLAPSE_CHANCE, WORLD_HEIGHT_TILES, BEDROCK_ROWS,
)
from game.world.tile_registry import AIR_ID, STONE_ID, WOOD_PLANK_ID, TORCH_ID, CHEST_ID, WORKBENCH_ID

HOUSE = "house"
RUINS = "ruins"
UNDERGROUND_ROOM = "underground_room"
ALL_KINDS = (HOUSE, RUINS, UNDERGROUND_ROOM)

# Every blueprint shares this 7-wide footprint (dx relative to the anchor
# column) -- wide enough for a real little room, narrow enough that
# STRUCTURE_MARGIN_TILES comfortably prevents neighboring slots' footprints
# from ever overlapping.
_FOOTPRINT_DX = range(-3, 4)


class StructureInstance(NamedTuple):
    kind: str
    anchor_x: int
    anchor_y: int  # surface row for House/Ruins, a chosen depth row for Underground Room
    columns: Dict[int, Dict[int, int]]


def _new_columns() -> Dict[int, Dict[int, int]]:
    return {dx: {} for dx in _FOOTPRINT_DX}


def _house_blueprint() -> Dict[int, Dict[int, int]]:
    """A small wooden house: floor, 3-tile interior, a doorway, a Torch, a
    Chest, and a Workbench -- worth walking into, not just looking at. The
    whole interior is explicitly forced to AIR_ID (not just left unset),
    since the natural terrain there could otherwise still hold a tree/
    crate/bush from decoration -- generate_column runs decoration before
    structures (see its module docstring), so a structure must actively
    clear its own interior rather than assume it's already empty."""
    cols = _new_columns()
    for dx in _FOOTPRINT_DX:
        cols[dx][0] = WOOD_PLANK_ID  # floor
        cols[dx][-4] = WOOD_PLANK_ID  # roof
    for dy in (-1, -2, -3):
        for dx in _FOOTPRINT_DX:
            cols[dx][dy] = WOOD_PLANK_ID if dx in (-3, 3) else AIR_ID
    cols[2][-1] = CHEST_ID
    cols[-2][-1] = WORKBENCH_ID
    cols[-2][-2] = TORCH_ID
    return cols


def _ruins_blueprint(rng: random.Random) -> Dict[int, Dict[int, int]]:
    """The same footprint as House, built from Stone, no roof, and each
    wall tile independently has RUINS_WALL_COLLAPSE_CHANCE of being left
    out of the blueprint entirely -- unlike every other cell here, a
    collapsed wall tile is deliberately NOT forced to AIR_ID, so whatever
    natural terrain/decoration is already there (a tree branch, bare sky)
    shows through the gap, reading as reclaimed-by-nature decay. The
    floor, interior walking space, and Chest are always guaranteed clear."""
    cols = _new_columns()
    for dx in _FOOTPRINT_DX:
        cols[dx][0] = STONE_ID  # floor always intact
    for dy in (-1, -2, -3):
        for dx in _FOOTPRINT_DX:
            if dx not in (-3, 3):
                cols[dx][dy] = AIR_ID  # interior always cleared for walkability
            elif rng.random() >= RUINS_WALL_COLLAPSE_CHANCE:
                cols[dx][dy] = STONE_ID
            # else: left out of the blueprint -- a collapsed wall gap.
    cols[2][-1] = CHEST_ID
    return cols


def _underground_room_blueprint(wall_tile_id: int) -> Dict[int, Dict[int, int]]:
    """A room forcibly carved out of rock, regardless of what was there
    (solid stone, ore, natural cave air) -- walls/ceiling built from the
    anchor column's own biome underground_tile_id (so a room in the Desert
    reads as carved from Desert Stone, not generic Stone), a Wood Plank
    floor, a Torch, a Chest. Force-carving (vs. finding an existing pocket,
    like the moving hazards do) is a deliberate simplification that keeps
    this a pure function of (seed, slot_index)."""
    cols = _new_columns()
    for dx in _FOOTPRINT_DX:
        cols[dx][0] = WOOD_PLANK_ID  # floor
        cols[dx][-4] = wall_tile_id  # ceiling
    for dy in (-1, -2, -3):
        for dx in _FOOTPRINT_DX:
            cols[dx][dy] = wall_tile_id if dx in (-3, 3) else AIR_ID
    cols[-2][-2] = TORCH_ID
    cols[2][-1] = CHEST_ID
    return cols


def structure_for_slot(seed: int, slot_index: int) -> Optional[StructureInstance]:
    """Pure function of (seed, slot_index): returns the StructureInstance
    that slot contains, or None. Re-derivable from any column -- see module
    docstring."""
    from game.world.world_generator import _column_rng, surface_height, biome_at

    rng = _column_rng(seed ^ 0x2F91D3, slot_index)
    if rng.random() >= STRUCTURE_SPAWN_CHANCE_PER_SLOT:
        return None
    kind = rng.choice(ALL_KINDS)
    slot_start = slot_index * STRUCTURE_SLOT_WIDTH_TILES
    anchor_x = slot_start + rng.randint(
        STRUCTURE_MARGIN_TILES, STRUCTURE_SLOT_WIDTH_TILES - STRUCTURE_MARGIN_TILES - 1
    )

    if kind == UNDERGROUND_ROOM:
        anchor_surface_y = surface_height(seed, anchor_x)
        min_y = anchor_surface_y + UNDERGROUND_ROOM_MIN_DEPTH_BELOW_SURFACE
        max_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS - 6  # leaves clearance above bedrock
        if min_y >= max_y:
            return None
        anchor_y = rng.randint(min_y, max_y)
        wall_tile_id = biome_at(seed, anchor_x).underground_tile_id
        columns = _underground_room_blueprint(wall_tile_id)
    else:
        # Skip placement (reroll to "nothing") if the terrain across the
        # footprint is too uneven, so a House/Ruins never visibly floats
        # over a cliff or gap -- the "respecting terrain" requirement.
        anchor_surface_y = surface_height(seed, anchor_x)
        for edge_dx in (_FOOTPRINT_DX.start, _FOOTPRINT_DX.stop - 1):
            if abs(surface_height(seed, anchor_x + edge_dx) - anchor_surface_y) > STRUCTURE_MAX_TERRAIN_VARIANCE_TILES:
                return None
        anchor_y = anchor_surface_y
        columns = _house_blueprint() if kind == HOUSE else _ruins_blueprint(rng)

    return StructureInstance(kind=kind, anchor_x=anchor_x, anchor_y=anchor_y, columns=columns)


def place_structures(column: list, seed: int, x: int) -> None:
    """Overlays this column's slice of any structure whose footprint
    reaches x. Called last in world_generator.generate_column -- see
    module docstring for why."""
    home_slot = x // STRUCTURE_SLOT_WIDTH_TILES
    for slot_index in (home_slot - 1, home_slot, home_slot + 1):
        instance = structure_for_slot(seed, slot_index)
        if instance is None:
            continue
        dx = x - instance.anchor_x
        offsets = instance.columns.get(dx)
        if offsets is None:
            continue
        for dy, tile_id in offsets.items():
            column[instance.anchor_y + dy] = tile_id
