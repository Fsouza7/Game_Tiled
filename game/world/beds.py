"""Sleeping in a Bed: T while standing near one skips the world clock to
the next morning (WorldClock.skip_to_morning), but only at night and only
inside a real, bounded, walled-and-roofed space (see shelter.is_enclosed).
Kept out of GameApp, like every other gameplay rule (see
combat/combat_system.py, checkpoints.py, doors.py), so it's unit-testable
without needing a full GameApp/Renderer instance.
"""
from typing import Optional

from game.world import shelter
from game.world.world import World
from game.core.world_clock import WorldClock


def try_sleep(world: World, world_clock: WorldClock, tile_x: int, tile_y: int) -> Optional[str]:
    """Returns None on success (the clock has been skipped to morning);
    otherwise a human-readable reason nothing happened, for InputHandler
    to surface as a notification -- same shape as
    Player.blocked_mining_reason."""
    if not world_clock.is_night:
        return "You can only sleep at night"
    if not shelter.is_enclosed(world, tile_x, tile_y):
        return "This isn't a safe, enclosed shelter"
    world_clock.skip_to_morning()
    return None
