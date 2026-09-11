"""Deterministic procedural world generation.

Every column is generated purely as a function of (seed, x, y) -- no
dependency on neighboring columns or generation order. That is what lets
chunks be generated lazily, in any order, while still guaranteeing the same
seed always reproduces the same world.

Terrain height and caves use smooth sine-wave "value noise" instead of a
noise library, so Phase 1 has zero extra dependencies beyond the stdlib.
"""
import math
import random

from game.settings import (
    WORLD_HEIGHT_TILES,
    WORLD_WIDTH_TILES,
    SURFACE_BASE_HEIGHT,
    SURFACE_AMPLITUDE_1,
    SURFACE_AMPLITUDE_2,
    DIRT_LAYER_MIN,
    DIRT_LAYER_MAX,
    BEDROCK_ROWS,
    CAVE_THRESHOLD,
    CAVE_MIN_DEPTH_BELOW_SURFACE,
    ORE_MIN_DEPTH_BELOW_SURFACE,
    VOID_ORE_MIN_DEPTH_BELOW_SURFACE,
    VOID_ORE_SPAWN_CHANCE,
    BIOME_ZONE_WIDTH_TILES,
    CACTUS_SPAWN_CHANCE,
    CACTUS_TALL_CHANCE,
    TILE_SIZE,
    HAZARD_SPAWN_CHANCE_PER_COLUMN,
    HAZARD_MIN_DEPTH_BELOW_SURFACE_TILES,
    CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN,
    FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN,
    SURFACE_TRAP_SPAWN_CHANCE_PER_COLUMN,
)
from game.world.tile_registry import (
    AIR_ID, COAL_ORE_ID, IRON_ORE_ID, BEDROCK_ID,
    DECOR_CRATE_ID, TREE_ID, CACTUS_ID, BUSH_ID,
    SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID, FAN_ID,
    TRAP_SAND_ID, TRAP_MUD_ID, TRAP_ICE_ID, VOID_ORE_ID,
)
from game.world import biome_registry
from game.world.biome_registry import DESERT_ID, SNOW_ID, JUNGLE_ID
from game.world import hazard_feature
from game.world.hazard_feature import HazardAnchor
from game.world import structures

# Biome -> its thematic surface hazard (Forest deliberately has none, since
# the world's fixed always-Forest spawn window -- see biome_at -- should
# stay hazard-free).
_BIOME_SURFACE_TRAP_TILE = {
    DESERT_ID: TRAP_SAND_ID,
    SNOW_ID: TRAP_ICE_ID,
    JUNGLE_ID: TRAP_MUD_ID,
}
_CAVE_HAZARD_TILE_KINDS = (SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID)

CRATE_SPAWN_CHANCE = 0.015
BUSH_SPAWN_CHANCE = 0.05  # per column with no tree, Forest/Snow/Jungle only

# --- Trees ---
# The world is divided into fixed-width slots; each slot independently
# rolls whether it contains one tree, and at which column within the slot.
# This keeps tree placement a pure function of (seed, x) -- any column can
# work out whether it's a tree's own column, or just within a nearby tree's
# footprint, purely by re-deriving its slot's roll, with no dependency on
# neighboring columns having been generated yet -- while still guaranteeing
# trees never overlap (the slot width comfortably exceeds one tree sprite's
# 2-tile width). A tree is a single TREE_ID tile (see tile_registry.py and
# Renderer._draw_world's TREE_ID special case, which draws a real sprite
# from assets/Tiles/Trees.png spanning well beyond this one tile) -- there's
# no separate trunk/canopy role to track at the tile-grid level any more.
TREE_SLOT_WIDTH = 8
TREE_SPAWN_CHANCE_PER_SLOT = 0.35


def _column_rng(seed: int, x: int) -> random.Random:
    mixed = (seed * 374761393 + x * 668265263) & 0xFFFFFFFF
    return random.Random(mixed)


def _tree_center_for_slot(seed: int, slot_index: int):
    rng = _column_rng(seed ^ 0x7EE5, slot_index)
    if rng.random() < TREE_SPAWN_CHANCE_PER_SLOT:
        return slot_index * TREE_SLOT_WIDTH + rng.randint(1, TREE_SLOT_WIDTH - 2)
    return None


def _nearest_tree_center(seed: int, x: int):
    """Returns the tree's own column if `x` is within a 1-tile margin of a
    nearby tree (its own column, or a neighbor whose sprite may visually
    overlap it), else None. The 1-tile margin keeps other decoration
    (crates/bushes) from spawning directly under a tree's canopy overlap,
    same as the old canopy_left/canopy_right reservation."""
    home_slot = x // TREE_SLOT_WIDTH
    for slot_index in (home_slot - 1, home_slot, home_slot + 1):
        center = _tree_center_for_slot(seed, slot_index)
        if center is not None and abs(x - center) <= 1:
            return center
    return None


def _biome_zone_index(x: int) -> int:
    return x // BIOME_ZONE_WIDTH_TILES


def biome_at(seed: int, x: int):
    """Returns the BiomeDef for world column x. Pure function of (seed, x):
    each zone independently (and deterministically) rolls a biome, except
    within half a zone-width of the world's exact center, which is always
    Forest -- a fixed-radius safety window (not just "whichever zone the
    center happens to land in") so the spawn point has a guaranteed,
    symmetric margin of temperate ground regardless of the zone grid's
    alignment."""
    spawn_x = WORLD_WIDTH_TILES // 2
    if abs(x - spawn_x) < BIOME_ZONE_WIDTH_TILES // 2:
        return biome_registry.get("forest")

    zone = _biome_zone_index(x)
    rng = _column_rng(seed ^ 0xB10AE, zone)
    biomes = biome_registry.all_biomes()
    weights = [b.zone_weight for b in biomes]
    return rng.choices(biomes, weights=weights, k=1)[0]


def surface_height(seed: int, x: int) -> int:
    """Deterministic grass-line row for column x. Pure function of (seed, x)."""
    phase = seed % 1000
    wave1 = math.sin((x + phase) * 0.05) * SURFACE_AMPLITUDE_1
    wave2 = math.sin((x + phase) * 0.17 + 1.3) * SURFACE_AMPLITUDE_2
    height = SURFACE_BASE_HEIGHT + wave1 + wave2
    return max(10, min(WORLD_HEIGHT_TILES - 20, int(round(height))))


def _dirt_depth(seed: int, x: int) -> int:
    rng = _column_rng(seed ^ 0xD1A7, x)
    return rng.randint(DIRT_LAYER_MIN, DIRT_LAYER_MAX)


def _is_cave(seed: int, x: int, y: int) -> bool:
    n1 = math.sin(x * 0.09 + seed * 0.001) * math.cos(y * 0.11 + seed * 0.002)
    n2 = math.sin((x + y) * 0.045 + seed * 0.0007)
    value = (n1 + n2 + 2) / 4  # normalize to ~0..1
    return value > CAVE_THRESHOLD


def _ore_at(seed: int, x: int, y: int, biome) -> int:
    """Returns a tile id for (x, y) inside the deep underground: coal/iron
    are universal (found under every biome), then a chance at that biome's
    own exclusive ore (see `BiomeDef.exclusive_ore_tile_id`), else that
    biome's plain underground filler tile."""
    rng = random.Random((seed * 2654435761 + x * 40503 + y * 2246822519) & 0xFFFFFFFF)
    roll = rng.random()
    if roll < 0.02:
        return COAL_ORE_ID
    if roll < 0.032:
        return IRON_ORE_ID
    if biome.exclusive_ore_tile_id is not None and roll < 0.032 + biome.exclusive_ore_chance:
        return biome.exclusive_ore_tile_id
    return biome.underground_tile_id


def _void_ore_roll(seed: int, x: int, y: int) -> bool:
    """Independent roll (its own RNG stream, separate from `_ore_at`'s
    coal/iron/gem chances) for Voidstone: universal like coal/iron -- not
    gated to a single biome the way the gems are -- but only ever considered
    once a column is already past VOID_ORE_MIN_DEPTH_BELOW_SURFACE (see
    `generate_column`), and far rarer than Iron even then."""
    rng = random.Random((seed * 3266489917 + x * 2246822519 + y * 668265263) & 0xFFFFFFFF)
    return rng.random() < VOID_ORE_SPAWN_CHANCE


def generate_column(seed: int, x: int) -> list:
    """Generate the full vertical tile column for world x-coordinate x."""
    biome = biome_at(seed, x)
    surface_y = surface_height(seed, x)
    dirt_depth = _dirt_depth(seed, x)
    dirt_end_y = surface_y + dirt_depth
    bedrock_start_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS

    column = [AIR_ID] * WORLD_HEIGHT_TILES
    for y in range(WORLD_HEIGHT_TILES):
        if y < surface_y:
            column[y] = AIR_ID
        elif y >= bedrock_start_y:
            column[y] = BEDROCK_ID
        elif y == surface_y:
            column[y] = _surface_tile_for(seed, x, biome)
        elif y < dirt_end_y:
            column[y] = biome.subsurface_tile_id
        else:
            # Caves are shared by every biome (same noise field regardless
            # of the surface above); the stone/ore filler underneath is
            # biome-specific (see `BiomeDef.underground_tile_id` /
            # `exclusive_ore_tile_id`, and README "How biomes work").
            depth_below_surface = y - surface_y
            if (
                depth_below_surface >= CAVE_MIN_DEPTH_BELOW_SURFACE
                and _is_cave(seed, x, y)
            ):
                column[y] = AIR_ID
            elif depth_below_surface >= ORE_MIN_DEPTH_BELOW_SURFACE:
                # Voidstone is checked as its own, separate branch (not a
                # rewrite of `_ore_at`'s coal/iron/gem chances) -- it's
                # universal like coal/iron, but only ever possible once deep
                # enough (VOID_ORE_MIN_DEPTH_BELOW_SURFACE), and rolled with
                # its own independent, much rarer chance.
                if (
                    depth_below_surface >= VOID_ORE_MIN_DEPTH_BELOW_SURFACE
                    and _void_ore_roll(seed, x, y)
                ):
                    column[y] = VOID_ORE_ID
                else:
                    column[y] = _ore_at(seed, x, y, biome)
            else:
                column[y] = biome.underground_tile_id

    if biome.id == DESERT_ID:
        _place_desert_decoration(column, seed, x, surface_y)
    else:
        _place_forest_decoration(column, seed, x, surface_y)

    _place_cave_hazard(column, seed, x, surface_y, bedrock_start_y)
    _place_fan_shaft(column, seed, x, surface_y, bedrock_start_y)
    structures.place_structures(column, seed, x)

    return column


def _surface_tile_for(seed: int, x: int, biome) -> int:
    """The tile for column x's surface row: normally the biome's own
    surface tile, but occasionally swapped for that biome's speed-altering
    surface trap (Loose Sand/Sticky Mud/Slick Ice) -- see
    `_BIOME_SURFACE_TRAP_TILE` above and README "How the second-pass traps
    work". Forest has no entry in that table, so it's never affected."""
    trap_tile_id = _BIOME_SURFACE_TRAP_TILE.get(biome.id)
    if trap_tile_id is not None:
        rng = _column_rng(seed ^ 0x5A27FA, x)
        if rng.random() < SURFACE_TRAP_SPAWN_CHANCE_PER_COLUMN:
            return trap_tile_id
    return biome.surface_tile_id


def _place_cave_hazard(column: list, seed: int, x: int, surface_y: int, bedrock_start_y: int) -> None:
    """One roll per column places at most one static cave-floor hazard
    (Spikes, Fire, Arrow Trap or Falling Platform) at a valid cave-floor
    spot -- environmental hazards the player finds while exploring, not
    something they craft/place themselves (see settings.py "Static
    cave-floor hazards")."""
    rng = _column_rng(seed ^ 0x9E3383, x)
    if rng.random() >= CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN:
        return
    kind = rng.choice(_CAVE_HAZARD_TILE_KINDS)
    min_y = surface_y + CAVE_MIN_DEPTH_BELOW_SURFACE
    for y in range(min_y, bedrock_start_y - 1):
        # An air tile with a solid floor beneath it and clear air above --
        # a spot the player can actually walk into and stand on.
        if column[y] == AIR_ID and column[y - 1] == AIR_ID and column[y + 1] != AIR_ID:
            column[y] = kind
            return


def _place_fan_shaft(column: list, seed: int, x: int, surface_y: int, bedrock_start_y: int) -> None:
    """A rarer roll than cave hazards: places a Fan at the floor of a small
    vertical air pocket (a mini vertical shaft), so its updraft has a few
    tiles of open air to actually push the player up through."""
    rng = _column_rng(seed ^ 0x7C21B1, x)
    if rng.random() >= FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN:
        return
    min_y = surface_y + CAVE_MIN_DEPTH_BELOW_SURFACE
    shaft_clearance = 4
    for y in range(min_y, bedrock_start_y - shaft_clearance):
        if column[y] != AIR_ID and all(
            column[y - i] == AIR_ID for i in range(1, shaft_clearance + 1)
        ):
            column[y] = FAN_ID
            return


def _place_forest_decoration(column: list, seed: int, x: int, surface_y: int) -> None:
    tree_center = _nearest_tree_center(seed, x)
    if tree_center is not None:
        if x == tree_center:
            column[surface_y - 1] = TREE_ID
        # else: within a neighboring tree's visual footprint but not its
        # own column -- nothing to place here, the tree's own tile draws a
        # sprite wide enough to overlap this column purely visually.
    else:
        # Crates and berry bushes never compete with trees (or each other)
        # for the same tile -- one roll picks at most one of the two.
        deco_rng = _column_rng(seed ^ 0xC4A7E, x)
        roll = deco_rng.random()
        if roll < CRATE_SPAWN_CHANCE:
            column[surface_y - 1] = DECOR_CRATE_ID
        elif roll < CRATE_SPAWN_CHANCE + BUSH_SPAWN_CHANCE:
            column[surface_y - 1] = BUSH_ID


def generate_hazard_anchor(seed: int, x: int):
    """Returns a `HazardAnchor` (Saw/Rock Head/Spike Head) for column x, or
    None. Pure function of (seed, x): re-derives its own column (same as
    `generate_column`) to find a valid underground air pocket -- no
    dependency on neighboring columns, so this is safe to call in any order
    exactly like the rest of world generation (see module docstring)."""
    roll_rng = _column_rng(seed ^ 0x4A2A5D, x)
    if roll_rng.random() >= HAZARD_SPAWN_CHANCE_PER_COLUMN:
        return None
    kind = roll_rng.choice(hazard_feature.ALL_KINDS)
    phase = roll_rng.random() * 2 * math.pi

    surface_y = surface_height(seed, x)
    column = generate_column(seed, x)
    min_y = surface_y + HAZARD_MIN_DEPTH_BELOW_SURFACE_TILES
    max_y = WORLD_HEIGHT_TILES - BEDROCK_ROWS - 3
    for y in range(min_y, max_y):
        # A solid ceiling with at least 2 clear tiles of air beneath it --
        # enough room for the hazard's own small oscillation.
        if column[y - 1] != AIR_ID and column[y] == AIR_ID and column[y + 1] == AIR_ID:
            anchor_x = x * TILE_SIZE + TILE_SIZE / 2
            anchor_y = y * TILE_SIZE + TILE_SIZE / 2
            return HazardAnchor(kind=kind, anchor_x=anchor_x, anchor_y=anchor_y, phase=phase)
    return None


def _place_desert_decoration(column: list, seed: int, x: int, surface_y: int) -> None:
    # Deserts have no trees -- a single-column cactus (sometimes 2 tiles
    # tall) or a crate instead, picked by one roll so they never collide.
    rng = _column_rng(seed ^ 0xC4A7E, x)
    roll = rng.random()
    if roll < CACTUS_SPAWN_CHANCE:
        column[surface_y - 1] = CACTUS_ID
        if rng.random() < CACTUS_TALL_CHANCE:
            column[surface_y - 2] = CACTUS_ID
    elif roll < CACTUS_SPAWN_CHANCE + CRATE_SPAWN_CHANCE:
        column[surface_y - 1] = DECOR_CRATE_ID
