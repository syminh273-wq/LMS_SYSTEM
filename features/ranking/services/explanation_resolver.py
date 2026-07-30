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


def explain_score(total_score: float, exam_count: int) -> str:
    score = round(float(total_score or 0), 2)
    count = int(exam_count or 0)
    if count == 0:
        return 'Chưa có bài thi nào được chấm điểm.'
    return (
        f'Điểm thành tích = {score} điểm (trung bình có trọng số từ {count} bài thi: '
        f'cuối kỳ ×3, giữa kỳ ×2, thường xuyên ×1).'
    )
