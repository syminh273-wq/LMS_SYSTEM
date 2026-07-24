"""Default XP rules. Run via `python manage.py seed_xp_rules` (TODO) or
inserted lazily on first read.

Stored in `ranking_xp_rules` (bucket=0). The XPService reads these per
event; if a rule is missing, the event still works as long as the caller
passes `delta_xp` explicitly.
"""
DEFAULT_RULES = [
    ('classroom_joined',          10, 'Tham gia lớp học'),
    ('attendance_present',         5, 'Có mặt tại buổi học'),

    ('exam_submitted',            20, 'Nộp bài thi'),
    ('exam_passed',               50, 'Đậu bài thi'),

    ('quiz_submitted',            10, 'Nộp bài quiz'),
    ('quiz_passed',               15, 'Đậu bài quiz'),
    ('quiz_perfect',              20, 'Đạt 100% bài quiz'),

    ('doc_completed',             10, 'Hoàn thành đọc tài liệu'),

    ('collection_completed',     100, 'Hoàn thành bộ quiz'),
    ('certificate_issued',       200, 'Nhận chứng chỉ'),
]


def seed_default_rules(repo):
    """Idempotently insert all default rules. Safe to call multiple times."""
    inserted = 0
    for event_type, amount, description in DEFAULT_RULES:
        existing = repo.get(event_type)
        if existing is None:
            repo.upsert(event_type, amount, is_active=True, description=description)
            inserted += 1
    return inserted
