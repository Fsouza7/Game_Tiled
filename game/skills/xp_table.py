"""The real RuneScape XP-to-level curve (levels 1-99): a deliberately
steep, authentic curve where early levels are fast and 99 is a genuine
long-term goal -- see README "How skills/leveling work". Built once at
import time from the well-known formula:

    xp(level) = floor(1/4 * sum_{n=1}^{level-1} floor(n + 300 * 2**(n/7)))

xp(1) = 0, xp(99) = 13,034,431 (a widely-documented reference value,
asserted in tests/test_skills.py as a sanity check on this formula).
"""

SKILL_MAX_LEVEL = 99


def _build_level_xp_table() -> list:
    table = [0] * (SKILL_MAX_LEVEL + 1)  # table[level] for level in 1..99; index 0 unused
    running_sum = 0
    for level in range(2, SKILL_MAX_LEVEL + 1):
        n = level - 1
        running_sum += int(n + 300.0 * 2.0 ** (n / 7.0))
        table[level] = int(running_sum / 4)
    return table


LEVEL_XP_TABLE = _build_level_xp_table()
MAX_XP = LEVEL_XP_TABLE[SKILL_MAX_LEVEL]


def level_for_xp(xp: float) -> int:
    """Highest level whose xp requirement is <= xp, clamped to
    [1, SKILL_MAX_LEVEL]."""
    level = 1
    for candidate in range(2, SKILL_MAX_LEVEL + 1):
        if xp < LEVEL_XP_TABLE[candidate]:
            break
        level = candidate
    return level
