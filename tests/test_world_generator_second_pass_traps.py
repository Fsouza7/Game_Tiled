"""Headless tests for the second-pass world-generated traps: static
cave-floor hazards (Spikes/Fire/Arrow Trap/Falling Platform), Fan shafts,
and per-biome surface traps (Loose Sand/Sticky Mud/Slick Ice) -- see
world_generator._place_cave_hazard / _place_fan_shaft / _surface_tile_for.

These were left half-wired (settings/tile registry present, placement
functions missing, `generate_column` calling an undefined
`_surface_tile_for`) -- this file locks in that they now actually place
tiles during world generation.
"""
from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES
from game.world.world_generator import generate_column, biome_at
from game.world.biome_registry import FOREST_ID, DESERT_ID, SNOW_ID, JUNGLE_ID
from game.world.tile_registry import (
    AIR_ID, SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID, FAN_ID,
    TRAP_SAND_ID, TRAP_MUD_ID, TRAP_ICE_ID,
)

_CAVE_HAZARD_IDS = {SPIKES_ID, FIRE_ID, ARROW_TRAP_ID, CRUMBLE_PLATFORM_ID}


def test_generate_column_does_not_crash():
    # Regression test: generate_column used to call an undefined
    # _surface_tile_for and raise NameError on every single column.
    for x in range(0, WORLD_WIDTH_TILES, 7):
        column = generate_column(DEFAULT_SEED, x)
        assert len(column) > 0


def test_cave_hazards_spawn_somewhere_in_a_wide_scan():
    found_kinds = set()
    for x in range(0, WORLD_WIDTH_TILES, 3):
        column = generate_column(DEFAULT_SEED, x)
        found_kinds |= (set(column) & _CAVE_HAZARD_IDS)
    assert found_kinds, "no cave hazard spawned anywhere -- check CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN/seed"


def test_cave_hazard_sits_on_a_solid_floor_with_air_above():
    for x in range(0, WORLD_WIDTH_TILES, 3):
        column = generate_column(DEFAULT_SEED, x)
        for y, tile_id in enumerate(column):
            if tile_id in _CAVE_HAZARD_IDS:
                assert column[y - 1] == AIR_ID
                assert column[y + 1] != AIR_ID
                return
    assert False, "no cave hazard found to check placement against"


def test_fan_shafts_spawn_with_clear_vertical_air_above():
    found = False
    for x in range(0, WORLD_WIDTH_TILES, 3):
        column = generate_column(DEFAULT_SEED, x)
        for y, tile_id in enumerate(column):
            if tile_id == FAN_ID:
                found = True
                assert all(column[y - i] == AIR_ID for i in range(1, 5))
    assert found, "no fan shaft spawned anywhere -- check FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN/seed"


def _surface_tiles_in_biome(seed: int, biome_id: str) -> set:
    tiles = set()
    for x in range(0, WORLD_WIDTH_TILES, 2):
        if biome_at(seed, x).id != biome_id:
            continue
        column = generate_column(seed, x)
        surface_y = next(y for y, t in enumerate(column) if t != AIR_ID)
        tiles.add(column[surface_y])
    return tiles


def test_desert_surface_sometimes_has_loose_sand():
    assert TRAP_SAND_ID in _surface_tiles_in_biome(DEFAULT_SEED, DESERT_ID)


def test_snow_surface_sometimes_has_slick_ice():
    assert TRAP_ICE_ID in _surface_tiles_in_biome(DEFAULT_SEED, SNOW_ID)


def test_jungle_surface_sometimes_has_sticky_mud():
    assert TRAP_MUD_ID in _surface_tiles_in_biome(DEFAULT_SEED, JUNGLE_ID)


def test_forest_surface_never_has_a_biome_surface_trap():
    tiles = _surface_tiles_in_biome(DEFAULT_SEED, FOREST_ID)
    assert not (tiles & {TRAP_SAND_ID, TRAP_MUD_ID, TRAP_ICE_ID})
