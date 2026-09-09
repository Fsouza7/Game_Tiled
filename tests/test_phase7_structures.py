"""Headless tests for Phase 7 procedural structures (House, Ruins,
Underground Room) -- see game/world/structures.py.
"""
from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, STRUCTURE_SLOT_WIDTH_TILES
from game.world import structures
from game.world.structures import HOUSE, RUINS, UNDERGROUND_ROOM
from game.world.world_generator import generate_column, surface_height
from game.world import tile_registry
from game.world.tile_registry import AIR_ID, CHEST_ID, TORCH_ID, WOOD_PLANK_ID

_SLOT_COUNT = WORLD_WIDTH_TILES // STRUCTURE_SLOT_WIDTH_TILES


def _all_instances(seed=DEFAULT_SEED):
    instances = []
    for slot_index in range(_SLOT_COUNT):
        instance = structures.structure_for_slot(seed, slot_index)
        if instance is not None:
            instances.append(instance)
    return instances


def test_every_structure_kind_spawns_somewhere():
    kinds = {instance.kind for instance in _all_instances()}
    assert kinds == {HOUSE, RUINS, UNDERGROUND_ROOM}, \
        f"missing kinds -- check STRUCTURE_SPAWN_CHANCE_PER_SLOT/seed: {kinds}"


def test_no_two_structures_overlap():
    instances = _all_instances()
    occupied = []  # list of (min_x, max_x)
    for instance in instances:
        lo, hi = instance.anchor_x - 3, instance.anchor_x + 3
        for other_lo, other_hi in occupied:
            assert hi < other_lo or lo > other_hi, "two structures' footprints overlap"
        occupied.append((lo, hi))


def test_structure_blueprint_matches_the_generated_world():
    """Every (dx, dy) offset in a structure's blueprint must actually show
    up at the right world position once run through generate_column --
    this is the real integration test for place_structures, not just the
    blueprint dict in isolation."""
    instances = _all_instances()
    assert instances, "no structures spawned at all -- nothing to check"
    for instance in instances:
        for dx, offsets in instance.columns.items():
            column = generate_column(DEFAULT_SEED, instance.anchor_x + dx)
            for dy, expected_tile_id in offsets.items():
                assert column[instance.anchor_y + dy] == expected_tile_id


def test_house_and_ruins_floor_sits_at_their_own_columns_surface_height():
    for instance in _all_instances():
        if instance.kind not in (HOUSE, RUINS):
            continue
        assert instance.anchor_y == surface_height(DEFAULT_SEED, instance.anchor_x)


def test_chest_is_reachable_solid_floor_below_open_air_above():
    """The Chest always sits at (dx=2, dy=-1) with a solid floor at dy=0
    beneath it and open air at dy=-2/-3 above it -- so a player can
    actually walk up and reach it, not find it floating or walled in."""
    found_any = False
    for instance in _all_instances():
        offsets = instance.columns.get(2)
        if offsets is None or offsets.get(-1) != CHEST_ID:
            continue
        found_any = True
        floor_tile = tile_registry.get(instance.columns[2][0])
        assert floor_tile.solid
        column = generate_column(DEFAULT_SEED, instance.anchor_x + 2)
        assert column[instance.anchor_y - 2] == AIR_ID
    assert found_any


def test_underground_room_interior_is_hollowed_out():
    room = next(i for i in _all_instances() if i.kind == UNDERGROUND_ROOM)
    column = generate_column(DEFAULT_SEED, room.anchor_x)
    # Interior column (dx=0) rows -1..-3 are forced to AIR_ID regardless of
    # whatever solid rock/ore/cave-noise would naturally be there this deep.
    for dy in (-1, -2, -3):
        assert column[room.anchor_y + dy] == AIR_ID
    # Walls actually carved from solid material, not left open.
    assert tile_registry.get(column[room.anchor_y - 4]).solid  # ceiling
    left_wall_column = generate_column(DEFAULT_SEED, room.anchor_x - 3)
    assert tile_registry.get(left_wall_column[room.anchor_y - 2]).solid


def test_underground_room_walls_use_that_columns_own_biome_stone():
    """Regression: an early version hardcoded generic STONE_ID for every
    Underground Room's walls, which broke the Desert/Snow/Jungle
    underground-tile-purity tests (a Desert biome underground scan asserts
    STONE_ID never appears) -- walls must use the anchor's own biome
    underground_tile_id instead."""
    from game.world.world_generator import biome_at
    for instance in _all_instances():
        if instance.kind != UNDERGROUND_ROOM:
            continue
        expected_wall = biome_at(DEFAULT_SEED, instance.anchor_x).underground_tile_id
        assert instance.columns[-3][-2] == expected_wall
