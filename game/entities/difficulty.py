"""Day-based enemy difficulty scaling (user-requested: "cada dia que
passa os mobs ficam mais fortes"). Pure functions of day_count
(WorldClock.day_count) -> a multiplier; day 1 is always the unscaled
baseline (1.0x). Capped at ENEMY_DIFFICULTY_MAX_DAY so a very long
playthrough doesn't scale into absurd numbers.

Only freshly-spawned enemies pick up the current multiplier (baked into
the instance at creation time via Enemy.__init__'s health_multiplier/
damage_multiplier params) -- an enemy already alive when a new day ticks
over does not retroactively get tougher, same "state is snapshotted at
spawn" precedent difficulty-adjacent systems elsewhere in this project
already use (e.g. a summon's stats are fixed at cast time).
"""
from game.settings import ENEMY_HEALTH_PCT_PER_DAY, ENEMY_DAMAGE_PCT_PER_DAY, ENEMY_DIFFICULTY_MAX_DAY


def _scaling_days(day_count: int) -> int:
    """Day 1 -> 0 scaling days (baseline); each day after that up to the
    cap adds one more day's worth of growth."""
    return max(0, min(day_count - 1, ENEMY_DIFFICULTY_MAX_DAY - 1))


def health_multiplier(day_count: int) -> float:
    return 1.0 + _scaling_days(day_count) * ENEMY_HEALTH_PCT_PER_DAY


def damage_multiplier(day_count: int) -> float:
    return 1.0 + _scaling_days(day_count) * ENEMY_DAMAGE_PCT_PER_DAY
