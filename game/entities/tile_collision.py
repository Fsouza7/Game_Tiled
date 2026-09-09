"""Shared AABB-vs-tile-grid collision, used by every physical entity
(Player, Enemy) so the resolution logic exists in exactly one place.

An "entity" here is anything with .x, .y, .width, .height, .x_vel, .y_vel
(see Entity in entity.py).
"""
from game.settings import TILE_SIZE
from game.world.world import World


def move_axis(entity, world: World, delta: float, horizontal: bool) -> bool:
    """Moves entity by `delta` along one axis and resolves collisions.

    Mutates entity.x/y (clamped to the tile it collided with) and zeroes
    the matching velocity component on collision. Returns True only for a
    downward vertical move that hit the ground (i.e. "landed this frame");
    every other case (including horizontal collisions) returns False.
    """
    if delta == 0:
        return False
    if horizontal:
        entity.x += delta
    else:
        entity.y += delta

    rect = entity.rect
    left_tile = rect.left // TILE_SIZE
    right_tile = (rect.right - 1) // TILE_SIZE
    top_tile = rect.top // TILE_SIZE
    bottom_tile = (rect.bottom - 1) // TILE_SIZE

    if horizontal:
        if delta > 0:
            for ty in range(top_tile, bottom_tile + 1):
                if world.is_solid(right_tile, ty):
                    entity.x = right_tile * TILE_SIZE - entity.width
                    entity.x_vel = 0.0
                    return False
        else:
            for ty in range(top_tile, bottom_tile + 1):
                if world.is_solid(left_tile, ty):
                    entity.x = (left_tile + 1) * TILE_SIZE
                    entity.x_vel = 0.0
                    return False
        return False
    else:
        if delta > 0:
            for tx in range(left_tile, right_tile + 1):
                if world.is_solid(tx, bottom_tile):
                    entity.y = bottom_tile * TILE_SIZE - entity.height
                    return True
        else:
            for tx in range(left_tile, right_tile + 1):
                if world.is_solid(tx, top_tile):
                    entity.y = (top_tile + 1) * TILE_SIZE
                    entity.y_vel = 0.0
                    return False
        return False


def _current_tile_column(entity) -> int:
    return int(entity.center_x // TILE_SIZE)


def is_solid_ahead(entity, world: World, direction: int) -> bool:
    """True if a solid wall blocks the tile column the entity is about to
    step into -- used by ground AI to turn around instead of walking into
    it. Based on the entity's current column (not its edge position): for
    an entity narrower than one tile, "edge + width" can still land inside
    its own column and never actually reach the next one."""
    probe_x = _current_tile_column(entity) + direction
    mid_y = int((entity.y + entity.height / 2) // TILE_SIZE)
    return world.is_solid(probe_x, mid_y)


def has_ground_ahead(entity, world: World, direction: int) -> bool:
    """True if there is solid ground just beyond the entity's leading edge
    -- used by ground AI to avoid walking off ledges."""
    probe_x = _current_tile_column(entity) + direction
    below_y = int((entity.y + entity.height) // TILE_SIZE)
    return world.is_solid(probe_x, below_y)
