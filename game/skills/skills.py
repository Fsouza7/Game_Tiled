"""Runtime skill/leveling state, one instance per Player (mirrors the role
Equipment plays for armor). See game/skills/xp_table.py for the XP curve
and skill_tree_registry.py for the tree nodes each skill's bonus helpers
below check.
"""
from typing import Dict, List, Set, Tuple

from game.skills import xp_table
from game.skills.skill_tree_registry import get as get_node
from game.settings import (
    ATTACK_DAMAGE_PCT_PER_LEVEL, MAGIC_DAMAGE_PCT_PER_LEVEL,
    MINING_POWER_PCT_PER_LEVEL, DEFENSE_FLAT_PER_LEVEL,
)

SKILL_IDS = ("attack", "defense", "magic", "mining", "crafting", "hitpoints")

SKILL_NAMES: Dict[str, str] = {
    "attack": "Attack", "defense": "Defense", "magic": "Magic",
    "mining": "Mining", "crafting": "Crafting", "hitpoints": "Hitpoints",
}


class SkillState:
    def __init__(self, xp: float = 0.0, unlocked_node_ids: Set[str] = None):
        self.xp = xp
        self.unlocked_node_ids: Set[str] = set(unlocked_node_ids) if unlocked_node_ids else set()


class Skills:
    def __init__(self):
        self._states: Dict[str, SkillState] = {skill_id: SkillState() for skill_id in SKILL_IDS}
        self.pending_level_ups: List[Tuple[str, int]] = []

    # --- xp / level ---
    def xp(self, skill_id: str) -> float:
        return self._states[skill_id].xp

    def restore_state(self, skill_id: str, xp: float, unlocked_node_ids: Set[str]) -> None:
        """Overwrites one skill's saved state wholesale -- used only by
        save_system.deserialize, which already has the exact xp/unlocked
        set from a prior save and isn't "granting" anything (no
        pending_level_ups should fire for state that's just being
        restored, not earned this session)."""
        state = self._states[skill_id]
        state.xp = xp
        state.unlocked_node_ids = set(unlocked_node_ids)

    def level(self, skill_id: str) -> int:
        return xp_table.level_for_xp(self._states[skill_id].xp)

    def add_xp(self, skill_id: str, amount: float) -> None:
        if amount <= 0:
            return
        state = self._states[skill_id]
        old_level = xp_table.level_for_xp(state.xp)
        state.xp = min(state.xp + amount, xp_table.MAX_XP)
        new_level = xp_table.level_for_xp(state.xp)
        for lvl in range(old_level + 1, new_level + 1):
            self.pending_level_ups.append((skill_id, lvl))

    def drain_level_ups(self) -> List[Tuple[str, int]]:
        drained = self.pending_level_ups
        self.pending_level_ups = []
        return drained

    def combat_level(self) -> int:
        """A simple average of Attack/Defense/Magic/Hitpoints -- a display-
        only flavor number, no mechanical effect."""
        levels = [self.level("attack"), self.level("defense"), self.level("magic"), self.level("hitpoints")]
        return round(sum(levels) / len(levels))

    # --- skill-point tree ---
    def unlocked_node_ids(self, skill_id: str) -> Set[str]:
        return self._states[skill_id].unlocked_node_ids

    def has_node(self, node_id: str) -> bool:
        node = get_node(node_id)
        return node_id in self._states[node.skill_id].unlocked_node_ids

    def available_points(self, skill_id: str) -> int:
        state = self._states[skill_id]
        level = xp_table.level_for_xp(state.xp)
        return max(0, (level - 1) - len(state.unlocked_node_ids))

    def try_unlock_node(self, node_id: str) -> bool:
        node = get_node(node_id)
        state = self._states[node.skill_id]
        if node_id in state.unlocked_node_ids:
            return False
        if node.requires_node_id is not None and node.requires_node_id not in state.unlocked_node_ids:
            return False  # a real chain: can't skip to a later tier
        if xp_table.level_for_xp(state.xp) < node.required_level:
            return False
        if self.available_points(node.skill_id) <= 0:
            return False
        state.unlocked_node_ids.add(node_id)
        return True

    # --- level-up progress (0.0 = just reached this level, 1.0 = about to level up) ---
    def level_progress_ratio(self, skill_id: str) -> float:
        level = self.level(skill_id)
        if level >= xp_table.SKILL_MAX_LEVEL:
            return 1.0
        current_threshold = xp_table.LEVEL_XP_TABLE[level]
        next_threshold = xp_table.LEVEL_XP_TABLE[level + 1]
        span = max(1, next_threshold - current_threshold)
        return max(0.0, min(1.0, (self.xp(skill_id) - current_threshold) / span))

    def combat_level_progress_ratio(self) -> float:
        """Average progress-to-next-level across the 4 skills combat_level()
        itself averages -- Combat Lv has no XP track of its own, so this is
        the closest honest "% toward the next tick" for the top HUD bar."""
        skills = ("attack", "defense", "magic", "hitpoints")
        return sum(self.level_progress_ratio(s) for s in skills) / len(skills)

    # --- combat/gathering stat helpers (explicit per-node checks, no
    # generic "effect engine" -- matches this codebase's established style) ---
    def attack_damage_multiplier(self) -> float:
        multiplier = 1.0 + ATTACK_DAMAGE_PCT_PER_LEVEL * (self.level("attack") - 1)
        if self.has_node("attack_keen_edge"):
            multiplier += 0.10
        if self.has_node("attack_berserker"):
            multiplier += 0.15
        if self.has_node("attack_deadly_precision"):
            multiplier += 0.20
        return multiplier

    def magic_damage_multiplier(self) -> float:
        multiplier = 1.0 + MAGIC_DAMAGE_PCT_PER_LEVEL * (self.level("magic") - 1)
        if self.has_node("magic_empowered_bond"):
            multiplier += 0.15
        if self.has_node("magic_arcane_mastery"):
            multiplier += 0.25
        return multiplier

    def mining_power_multiplier(self) -> float:
        multiplier = 1.0 + MINING_POWER_PCT_PER_LEVEL * self.level("mining")
        if self.has_node("mining_efficient_strikes"):
            multiplier += 0.20
        if self.has_node("mining_master_prospector"):
            multiplier += 0.30
        return multiplier

    def defense_flat_bonus(self) -> float:
        bonus = DEFENSE_FLAT_PER_LEVEL * self.level("defense")
        if self.has_node("defense_thick_skin"):
            bonus += 5.0
        if self.has_node("defense_unbreakable"):
            bonus += 10.0
        if self.has_node("defense_fortress"):
            bonus += 15.0
        return bonus

    def crafting_xp_multiplier(self) -> float:
        multiplier = 1.0
        if self.has_node("crafting_master"):
            multiplier += 0.5
        if self.has_node("crafting_artisan"):
            multiplier += 0.25
        return multiplier
