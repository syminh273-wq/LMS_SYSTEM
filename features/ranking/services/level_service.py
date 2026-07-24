"""Level catalog. Returns the full list of levels + thresholds so the FE
can render badges/progress without hardcoding curve constants."""
from features.ranking.services.level_math import required_xp_for_level, MAX_LEVEL


LEVEL_TITLES = {
    1:  'Tân binh',
    2:  'Học viên',
    3:  'Sơ cấp',
    5:  'Trung cấp',
    10: 'Cao cấp',
    15: 'Chuyên gia',
    20: 'Bậc thầy',
    30: 'Đại sư',
    50: 'Huyền thoại',
    100: 'Thần thoại',
}


def level_title(level: int) -> str:
    if level in LEVEL_TITLES:
        return LEVEL_TITLES[level]
    best = max((lvl for lvl in LEVEL_TITLES if lvl <= level), default=1)
    return LEVEL_TITLES[best]


def all_levels(max_level: int = None):
    max_level = max_level or min(50, MAX_LEVEL)
    out = []
    for lvl in range(1, max_level + 1):
        out.append({
            'level': lvl,
            'required_xp': required_xp_for_level(lvl),
            'title': level_title(lvl),
        })
    return out
