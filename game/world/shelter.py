"""Shelter detection for sleeping in a Bed: a bounded flood-fill (BFS)
from the bed's own tile, through every non-solid tile reachable from it.
If the fill exhausts -- hits solid walls/floor/roof on every side --
within SHELTER_MAX_AIR_TILES tiles, the space is small and fully
enclosed, a real "room". If the fill still has tiles left to visit when
the cap is hit, the space either leaks out into the open world or is
simply too big to read as a cozy, safe room -- either way, not sheltered.

Bounded cost regardless of world size, same "cap the traversal, don't
walk the whole world" principle chunk loading/lighting already use.
"""
from typing import Set, Tuple

from game.settings import SHELTER_MAX_AIR_TILES
from game.world.world import World


def is_enclosed(world: World, tile_x: int, tile_y: int) -> bool:
    if world.is_solid(tile_x, tile_y):
        return False  # the starting point itself must be open air

    visited: Set[Tuple[int, int]] = {(tile_x, tile_y)}
    frontier = [(tile_x, tile_y)]
    while frontier:
        x, y = frontier.pop()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (nx, ny) in visited or world.is_solid(nx, ny):
                continue
            visited.add((nx, ny))
            if len(visited) > SHELTER_MAX_AIR_TILES:
                return False  # leaked out (or too big) before running out of open tiles
            frontier.append((nx, ny))
    return True
