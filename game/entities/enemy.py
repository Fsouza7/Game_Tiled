"""Runtime enemy instance: an EnemyDef plus per-instance state (health,
facing, AI timers). AI behavior itself lives in enemy_ai.py to keep this
class a plain data holder."""
import random

from game.entities.entity import Entity
from game.entities.enemy_def import EnemyDef
from game.settings import TILE_SIZE, ENEMY_HIT_INVULNERABILITY_S
from game.rendering.damage_numbers import queue_popup


class Enemy(Entity):
    def __init__(
        self, enemy_def: EnemyDef, spawn_x_px: float, spawn_y_px: float,
        health_multiplier: float = 1.0, damage_multiplier: float = 1.0,
    ):
        width = enemy_def.width_tiles * TILE_SIZE
        height = enemy_def.height_tiles * TILE_SIZE
        super().__init__(spawn_x_px, spawn_y_px, width, height)

        self.enemy_def = enemy_def
        # Instance-level, difficulty-scaled stats (see game/entities/
        # difficulty.py) -- kept separate from enemy_def's own (frozen,
        # shared-across-every-instance) max_health/contact_damage so two
        # Slimes spawned on different days can have different toughness.
        # Defaults (1.0x) reproduce enemy_def's own numbers exactly.
        self.max_health = enemy_def.max_health * health_multiplier
        self.contact_damage = enemy_def.contact_damage * damage_multiplier
        self.health = self.max_health
        self.alive = True
        self.on_ground = False
        self.facing_right = random.choice((True, False))
        self.invulnerability_remaining = 0.0
        self.drop_collected = False
        self.defeated = False  # True only when killed by damage (not despawned)

        # AI scratch state (meaning depends on ai_type; see enemy_ai.py).
        self.hop_cooldown_remaining = random.uniform(0.0, 1.0)
        self.bob_phase = random.uniform(0.0, 6.28)
        self.bob_center_y = spawn_y_px  # flying enemies bob around this altitude
        self.pending_damage_popups = []

    def take_damage(self, amount: float) -> bool:
        """Returns True if this hit was applied (False if currently
        invulnerable)."""
        if not self.alive or self.invulnerability_remaining > 0.0:
            return False
        queue_popup(self, amount)
        self.health -= amount
        self.invulnerability_remaining = ENEMY_HIT_INVULNERABILITY_S
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.defeated = True
        return True

    def roll_drop(self):
        """Returns (item_id, quantity) or None."""
        d = self.enemy_def
        if d.drop_item_id is None or random.random() > d.drop_chance:
            return None
        quantity = random.randint(d.drop_min, d.drop_max)
        return d.drop_item_id, quantity
