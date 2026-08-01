import math
from typing import Tuple

MAX_LEVEL = 100


def required_xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    return int(round(100 * math.pow(level - 1, 1.5)))


def level_for_xp(total_xp: int) -> int:
    if total_xp <= 0:
        return 1
    level = 1
    while level < MAX_LEVEL:
        if total_xp < required_xp_for_level(level + 1):
            return level
        level += 1
    return MAX_LEVEL


def progress_for_xp(total_xp: int) -> Tuple[int, int, int, int, int, float]:
    """Return (level, current_level_xp, next_level_xp, progress_pct, xp_to_next, current_level_total)."""
    level = level_for_xp(total_xp)
    cur_required = required_xp_for_level(level)
    next_required = required_xp_for_level(level + 1) if level < MAX_LEVEL else cur_required
    if level >= MAX_LEVEL:
        return level, total_xp - cur_required, 0, 100, 0, total_xp - cur_required
    span = max(1, next_required - cur_required)
    earned = max(0, total_xp - cur_required)
    pct = min(100, int((earned / span) * 100))
    return level, earned, next_required - cur_required, pct, (next_required - total_xp), span
