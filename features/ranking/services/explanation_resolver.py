"""Map XP event types and score breakdowns to human-readable Vietnamese.

Used by:
    - /consumer/ranking/me/transactions/        (per-transaction explanation)
    - /.../classrooms/<uid>/leaderboard/        (per-entry explanation)
    - /consumer/ranking/me/classroom/<uid>/     (my-stats explanation)
"""


EVENT_TITLES = {
    'classroom_joined':     'Tham gia lớp học',
    'attendance_present':   'Điểm danh có mặt',
    'exam_submitted':       'Nộp bài thi',
    'exam_passed':          'Đậu bài thi',
    'quiz_submitted':       'Nộp bài quiz',
    'quiz_passed':          'Hoàn thành quiz',
    'quiz_perfect':         'Quiz đạt điểm tuyệt đối',
    'doc_completed':        'Hoàn thành tài liệu',
    'collection_completed': 'Hoàn thành bộ sưu tập',
    'certificate_issued':   'Nhận chứng chỉ',
}


def explain_event(event_type: str, delta_xp: int = 0, description: str = '') -> str:
    title = EVENT_TITLES.get(event_type or '', event_type or 'Hoạt động')
    prefix = f'+{int(delta_xp)} XP' if delta_xp else 'XP'
    if description and description != (event_type or ''):
        return f'{prefix} — {title} ({description})'
    return f'{prefix} — {title}'


def explain_xp_history_row(tx) -> str:
    if tx is None:
        return ''
    return explain_event(
        getattr(tx, 'event_type', ''),
        int(getattr(tx, 'delta_xp', 0) or 0),
        getattr(tx, 'description', '') or '',
    )


def explain_score(quiz_avg: float, exam_avg: float, attendance_pct: float) -> str:
    qa = round(float(quiz_avg or 0), 2)
    ea = round(float(exam_avg or 0), 2)
    ap = round(float(attendance_pct or 0), 2)
    return (
        f'Điểm thành tích = {qa}% quiz (×0.6) + {ea}% exam (×0.4). '
        f'Điểm danh {ap}%.'
    )


def explain_xp_level(level: int, total_xp: int) -> str:
    from features.ranking.services.level_service import level_title
    return f'Cấp {level} ({level_title(level)}) — {int(total_xp or 0)} XP tích lũy'
