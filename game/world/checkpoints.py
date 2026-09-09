"""Checkpoint activation: touching a Checkpoint tile (tile_registry.CHECKPOINT_ID)
makes it the player's new respawn point. Kept out of GameApp, like every
other gameplay rule (see combat/combat_system.py), so it's unit-testable
without needing a full GameApp/Renderer instance.
"""
from game.settings import TILE_SIZE
from game.world.world import World
from game.world import tile_registry


def try_activate(player, world: World) -> bool:
    """Returns True iff this call just activated a *new* checkpoint (the
    caller uses that to fire a one-time confetti burst rather than one
    every frame the player stands on an already-active tile)."""
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    if world.get_tile(tile_x, tile_y) != tile_registry.CHECKPOINT_ID:
        return False
    spawn_x, spawn_y = tile_x * TILE_SIZE, tile_y * TILE_SIZE
    if (player.spawn_x, player.spawn_y) == (spawn_x, spawn_y):
        return False
    player.spawn_x, player.spawn_y = spawn_x, spawn_y
    return True
