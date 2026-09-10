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


def _leading_tile_column(entity, direction: int) -> int:
    """The tile column at the entity's actual leading edge in `direction`,
    or its center column if that reaches farther (never nearer) -- the
    probe base for is_solid_ahead/try_step_up. Center-only was the
    original design ("edge + width can still land inside its own column
    and never reach the next one" for a narrow entity), which is exactly
    right for a ~1-tile-wide regular enemy but badly undershoots a wide
    one: the Slime King boss is 2.4 tiles wide, so its real leading edge
    (what move_axis's own collision resolves against) can sit a full tile
    or more past center+1 -- a bump only there, not at center+1, went
    completely undetected, letting the boss's wide body catch a 2-tile
    total rise across its own width on an otherwise smooth 1-tile-per-
    column staircase (the reported "preso em terreno desnivelado")."""
    center_col = int(entity.center_x // TILE_SIZE)
    if entity.width <= TILE_SIZE:
        # No entity this size has ever shipped needing the edge-aware path
        # below, and it does change probe columns for one right at a tile
        # boundary (e.g. a narrow WALK enemy mid-step) versus pure
        # center+direction -- skip it entirely rather than risk nudging
        # existing ground-AI edge cases that already rely on the exact
        # center-only column.
        return center_col
    if direction > 0:
        edge_col = int((entity.x + entity.width - 1) // TILE_SIZE)
        return max(center_col, edge_col)
    edge_col = int(entity.x // TILE_SIZE)
    return min(center_col, edge_col)


def _entity_row_span(entity):
    """The tile rows an entity's hitbox actually occupies, top to bottom
    inclusive -- for the ~1-tile-tall regular enemies this is always a
    single row, but a taller entity (e.g. the 1.8-tile Slime King boss)
    spans two, and a check against only its mid-height row would miss a
    bump sitting at its feet while its middle is already clear."""
    top_tile = int(entity.y // TILE_SIZE)
    bottom_tile = int((entity.y + entity.height - 1) // TILE_SIZE)
    return range(top_tile, bottom_tile + 1)


def is_solid_ahead(entity, world: World, direction: int) -> bool:
    """True if a solid wall blocks the tile column the entity is about to
    step into -- used by ground AI to turn around instead of walking into
    it. Checks every row the entity's own height spans, not just its
    mid-height, so a taller entity can't clip a low bump its middle would
    otherwise clear (see _leading_tile_column for the column choice)."""
    probe_x = _leading_tile_column(entity, direction) + direction
    return any(world.is_solid(probe_x, ty) for ty in _entity_row_span(entity))


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
    probe_x = _leading_tile_column(entity, direction) + direction
    below_y = int((entity.y + entity.height) // TILE_SIZE)
    return world.is_solid(probe_x, below_y) or world.is_solid(probe_x, below_y + 1)


def try_step_up(entity, world: World, direction: int, max_step_tiles: int = 1) -> bool:
    """If the tiles blocking `direction` at the entity's leading edge (see
    _leading_tile_column) amount to no more than `max_step_tiles` of clean
    rise -- every row above the highest blocked one is clear, and there's
    headroom above the entity's own current position to rise into -- snaps
    it up by that many tiles and returns True. Returns False (and leaves
    the entity untouched) for a taller, genuinely unclimbable wall, or if
    nothing is blocking in the first place.

    `max_step_tiles` defaults to 1, right for the ~1-tile bumps regular
    ground AI needs to climb. The Slime King boss passes 2: at 2.4 tiles
    wide and up to ~9px/frame, its leading edge can reach a column whose
    ground is a full 2 tiles higher than the column under its own center,
    even though each individual column-to-column step in the generated
    terrain is only ever 1 tile (see _leading_tile_column's docstring) --
    a single-tile step-up would correctly detect *a* bump there but still
    reject it as "taller than climbable" and leave the boss stuck.

    Ground AI has no jump input the way the player does, so without this
    it would turn around (WALK) or stall dead against the bump for a full
    attack cycle (HOP) at every rise in the terrain -- which, given how
    bumpy generated ground already is, made ground enemies unable to make
    real progress, or in the HOP case, look like they were bouncing in
    place against an invisible wall."""
    rows = list(_entity_row_span(entity))
    top_tile, bottom_tile = rows[0], rows[-1]
    own_x = _current_tile_column(entity)
    probe_x = _leading_tile_column(entity, direction) + direction

    step = 0
    while step < max_step_tiles and world.is_solid(probe_x, bottom_tile - step):
        step += 1
    if step == 0:
        return False  # nothing blocking at ground level -- not a ledge at all
    if world.is_solid(probe_x, bottom_tile - step):
        return False  # still blocked past our climbing cap -- too tall to climb

    new_top = top_tile - step
    for ty in range(new_top - 1, top_tile):
        if world.is_solid(probe_x, ty) or world.is_solid(own_x, ty):
            return False  # no headroom to rise into, at the target or from here
    entity.y -= step * TILE_SIZE
    return True
