"""Door toggling: T while standing near a placed Door swaps it between
its closed (solid) and open (passable) tile id -- the same "swap the
stored tile id" trick Falling Platform already uses for its crumble/
respawn transition (World.set_tile), just player-driven instead of
timer-driven. Kept out of GameApp, like every other gameplay rule (see
combat/combat_system.py, checkpoints.py), so it's unit-testable without
needing a full GameApp/Renderer instance.
"""
from game.world.world import World
from game.world import tile_registry


def toggle(world: World, tile_x: int, tile_y: int) -> None:
    current = world.get_tile(tile_x, tile_y)
    if current == tile_registry.DOOR_CLOSED_ID:
        world.set_tile(tile_x, tile_y, tile_registry.DOOR_OPEN_ID)
    elif current == tile_registry.DOOR_OPEN_ID:
        world.set_tile(tile_x, tile_y, tile_registry.DOOR_CLOSED_ID)
