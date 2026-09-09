"""Runtime summon instance: a SummonDef plus per-instance state (facing,
attack cooldown, AI scratch state). Behavior lives in summon_ai.py to keep
this class a plain data holder, same split as enemy.py/enemy_ai.py.

Deliberate simplification: summons cannot take damage in this pass -- no
take_damage, enemies never target them (there's no "enemy attacks a
friendly entity" combat path anywhere in the game yet). `alive` exists
only so a summon can be dismissed (replaced by casting a different rod)
the same way enemies are pruned, not because anything currently kills one.
"""
import random

from game.entities.entity import Entity
from game.entities.summon_def import SummonDef
from game.settings import TILE_SIZE


class Summon(Entity):
    def __init__(self, summon_def: SummonDef, spawn_x_px: float, spawn_y_px: float):
        width = summon_def.width_tiles * TILE_SIZE
        height = summon_def.height_tiles * TILE_SIZE
        super().__init__(spawn_x_px, spawn_y_px, width, height)

        self.summon_def = summon_def
        self.alive = True
        self.facing_right = True
        self.attack_cooldown_remaining = 0.0

        # Mutable per-instance stats, seeded from summon_def but free to
        # diverge -- move_speed / attack_interval_s are still baked at
        # cast from the Magic tree's Swift Familiar node. Damage is *not*:
        # Magic's per-level multiplier is applied live in
        # combat_system.resolve_summon_attacks so a Magic level-up mid-fight
        # is visible on the next hit without recasting the rod.
        self.damage = summon_def.damage
        self.move_speed = summon_def.move_speed
        self.attack_interval_s = summon_def.attack_interval_s

        # AI scratch state (idle hover bob, mirrors Enemy's bob_phase).
        self.bob_phase = random.uniform(0.0, 6.28)
