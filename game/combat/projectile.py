"""A player-fired projectile (e.g. an arrow). Moves in a straight line with
a light gravity arc, destroyed on hitting a solid tile, an enemy, or timing
out."""
from game.entities.entity import Entity
from game.settings import TILE_SIZE, PROJECTILE_SIZE_TILES, PROJECTILE_LIFETIME_S


class Projectile(Entity):
    def __init__(
        self, x_px: float, y_px: float, x_vel: float, y_vel: float, damage: float,
        *, uses_magic: bool = False, affected_by_gravity: bool = True,
    ):
        size = PROJECTILE_SIZE_TILES * TILE_SIZE
        super().__init__(x_px, y_px, size, size)
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.damage = damage
        self.time_remaining = PROJECTILE_LIFETIME_S
        self.alive = True
        self.uses_magic = uses_magic
        self.affected_by_gravity = affected_by_gravity
