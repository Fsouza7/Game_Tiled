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
    """True if there is solid ground just beyond the entity's leading edge,
    at the entity's current height OR one tile below it -- used by ground
    AI to avoid walking off a real ledge. The one-tile tolerance mirrors
    try_step_up's upward one: a small step down is an ordinary bit of
    bumpy terrain (gravity just carries the entity down onto it), not a
    hazard -- treating any downward bump the same as a bottomless drop
    made ground AI reverse away from perfectly safe ground, which could
    dead-end it against a wall on the only other direction it could turn
    (both sides then permanently reversing every frame, net velocity 0)."""
    probe_x = _current_tile_column(entity) + direction
    below_y = int((entity.y + entity.height) // TILE_SIZE)
    return world.is_solid(probe_x, below_y) or world.is_solid(probe_x, below_y + 1)


def try_step_up(entity, world: World, direction: int) -> bool:
    """If the tile blocking `direction` (per is_solid_ahead) is only a
    single-tile-high ledge -- the row directly above it is clear -- snaps
    the entity up onto it and returns True. Returns False (and leaves the
    entity untouched) for a taller, genuinely unclimbable wall, or if
    nothing is blocking in the first place.

    Ground AI has no jump input the way the player does, so without this
    it would turn around at every 1-tile rise in the terrain -- which,
    given how bumpy generated ground already is, made ground enemies
    unable to go more than a tile or two before reversing course."""
    own_x = _current_tile_column(entity)
    probe_x = own_x + direction
    mid_y = int((entity.y + entity.height / 2) // TILE_SIZE)
    if not world.is_solid(probe_x, mid_y):
        return False
    if world.is_solid(probe_x, mid_y - 1) or world.is_solid(own_x, mid_y - 1):
        # Either the ledge itself is taller than one tile, or there's no
        # headroom to rise into from where the entity already stands (e.g.
        # a low cave corridor) -- either way, not climbable.
        return False
    entity.y = mid_y * TILE_SIZE - entity.height
    return True
