"""A boss is an Enemy with extra phase-tracking state (see boss_ai.py for
the AI itself, kept as a pure function the same way enemy_ai.py is). Reusing
Enemy means a Boss gets melee/ranged/summon damage, contact damage, drops
and save/load transience for free -- see combat_system.py and GameApp.
"""
from game.entities.enemy import Enemy
from game.entities.enemy_def import EnemyDef


class Boss(Enemy):
    def __init__(self, enemy_def: EnemyDef, spawn_x_px: float, spawn_y_px: float):
        super().__init__(enemy_def, spawn_x_px, spawn_y_px)
        self.phase_index = 0  # 0/1/2 -- see BOSS_PHASE_2/3_HEALTH_RATIO
        self.ranged_cooldown_remaining = 1.0
        self.enraged = False  # guards the one-shot minion summon on entering phase 2 (index)
        self.stomp_pending = False  # set by boss_ai on a phase-3 landing; consumed by combat_system.resolve_boss_stomp
