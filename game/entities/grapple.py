"""Pure raycast helper for the Grapple Hook accessory: steps along an aim
direction in small increments looking for the first solid tile, kept
separate from Player so it's independently testable -- same
separation-of-concerns precedent as tile_collision.py.
"""
from typing import Optional, Tuple

from game.settings import TILE_SIZE, GRAPPLE_MAX_RANGE_TILES, GRAPPLE_STEP_TILES
from game.world.world import World


def find_hook_anchor(world: World, origin_x: float, origin_y: float, aim_dx: float, aim_dy: float) -> Optional[Tuple[float, float]]:
    """Steps from (origin_x, origin_y) along the (aim_dx, aim_dy) unit
    vector, up to GRAPPLE_MAX_RANGE_TILES, looking for the first solid
    tile. Returns the last clear point (just short of that wall), or
    None if nothing solid is within range."""
    step_px = GRAPPLE_STEP_TILES * TILE_SIZE
    max_steps = int(GRAPPLE_MAX_RANGE_TILES / GRAPPLE_STEP_TILES)
    x, y = origin_x, origin_y
    for _ in range(max_steps):
        next_x = x + aim_dx * step_px
        next_y = y + aim_dy * step_px
        tile_x, tile_y = int(next_x // TILE_SIZE), int(next_y // TILE_SIZE)
        if world.is_solid(tile_x, tile_y):
            return x, y
        x, y = next_x, next_y
    return None
