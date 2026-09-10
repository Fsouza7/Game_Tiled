"""Fog-of-war map data backing the full Map screen (M).

The world is divided into MAP_CELL_SIZE_TILES x MAP_CELL_SIZE_TILES cells.
A cell becomes "explored" -- and gets a fixed representative color, sampled
once -- the first time the player comes within MAP_REVEAL_RADIUS_TILES of
it. Sampling a single tile at the cell's center (rather than averaging the
whole cell) is a deliberate simplification, the same "one value per region,
no true detail" tradeoff the lighting system already makes for the same
reason (see lighting.py) -- a mixed-terrain cell just shows whichever tile
happens to sit at its middle.

World.explored_cells (a plain dict, cell -> RGB color) is the only state
this owns; it's cheap enough to keep every explored cell forever (a few
thousand cells even after a long session) and to save/restore whole.
"""
from typing import Tuple

from game.settings import (
    TILE_SIZE, MAP_CELL_SIZE_TILES, MAP_REVEAL_RADIUS_TILES,
    WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES,
)
from game.world import tile_registry
from game.world.tile_registry import AIR_ID

SKY_COLOR = (120, 170, 255)
CAVE_AIR_COLOR = (25, 25, 35)


def _cell_color(world, tile_x: int, tile_y: int) -> Tuple[int, int, int]:
    tile_id = world.get_tile(tile_x, tile_y)
    if tile_id == AIR_ID:
        return SKY_COLOR if tile_y < world.surface_height_at(tile_x) else CAVE_AIR_COLOR
    return tile_registry.get(tile_id).color


def reveal_around(world, center_x_px: float, center_y_px: float) -> None:
    """Marks every not-yet-explored cell within MAP_REVEAL_RADIUS_TILES of
    (center_x_px, center_y_px) as explored, sampling+caching its color.
    Cheap to call every frame: already-explored cells are skipped via a
    single dict lookup, so the real per-tile sampling cost is only ever
    paid once per cell, the first time it's revealed."""
    center_tile_x = int(center_x_px // TILE_SIZE)
    center_tile_y = int(center_y_px // TILE_SIZE)
    center_cell_x = center_tile_x // MAP_CELL_SIZE_TILES
    center_cell_y = center_tile_y // MAP_CELL_SIZE_TILES
    cell_radius = MAP_REVEAL_RADIUS_TILES // MAP_CELL_SIZE_TILES + 1
    radius_tiles_sq = MAP_REVEAL_RADIUS_TILES * MAP_REVEAL_RADIUS_TILES

    for cell_x in range(center_cell_x - cell_radius, center_cell_x + cell_radius + 1):
        for cell_y in range(center_cell_y - cell_radius, center_cell_y + cell_radius + 1):
            key = (cell_x, cell_y)
            if key in world.explored_cells:
                continue
            sample_tile_x = cell_x * MAP_CELL_SIZE_TILES + MAP_CELL_SIZE_TILES // 2
            sample_tile_y = cell_y * MAP_CELL_SIZE_TILES + MAP_CELL_SIZE_TILES // 2
            if not world.in_bounds(sample_tile_x, sample_tile_y):
                continue
            dx = sample_tile_x - center_tile_x
            dy = sample_tile_y - center_tile_y
            if dx * dx + dy * dy > radius_tiles_sq:
                continue
            world.explored_cells[key] = _cell_color(world, sample_tile_x, sample_tile_y)


def reveal_all(world) -> None:
    """Marks every cell of the entire world as explored -- a debug/cheat
    shortcut (see GameApp.debug_reveal_map), the same per-cell sampling
    reveal_around uses above, just with no radius limit or player
    position involved. Forces every not-yet-loaded chunk to generate (a
    cheap, deterministic, pure function of seed+column -- see
    world_generator.py's module docstring) since sampling a cell means
    reading a tile in it; a one-time cost, acceptable for a debug action."""
    max_cell_x = WORLD_WIDTH_TILES // MAP_CELL_SIZE_TILES
    max_cell_y = WORLD_HEIGHT_TILES // MAP_CELL_SIZE_TILES
    for cell_x in range(max_cell_x + 1):
        for cell_y in range(max_cell_y + 1):
            key = (cell_x, cell_y)
            if key in world.explored_cells:
                continue
            sample_tile_x = cell_x * MAP_CELL_SIZE_TILES + MAP_CELL_SIZE_TILES // 2
            sample_tile_y = cell_y * MAP_CELL_SIZE_TILES + MAP_CELL_SIZE_TILES // 2
            if not world.in_bounds(sample_tile_x, sample_tile_y):
                continue
            world.explored_cells[key] = _cell_color(world, sample_tile_x, sample_tile_y)
