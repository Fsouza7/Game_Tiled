"""An enemy/boss-fired projectile -- the mirror of projectile.py's
player-fired Projectile, but resolved against the player instead of
enemies (see combat_system.update_enemy_projectiles). Currently only the
Slime King's ranged Slime Lob attack creates these (see boss_ai.py)."""
from game.entities.entity import Entity
from game.settings import TILE_SIZE, ENEMY_PROJECTILE_SIZE_TILES, ENEMY_PROJECTILE_LIFETIME_S


class EnemyProjectile(Entity):
    def __init__(self, x_px: float, y_px: float, x_vel: float, y_vel: float, damage: float):
        size = ENEMY_PROJECTILE_SIZE_TILES * TILE_SIZE
        super().__init__(x_px, y_px, size, size)
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.damage = damage
        self.time_remaining = ENEMY_PROJECTILE_LIFETIME_S
        self.alive = True
