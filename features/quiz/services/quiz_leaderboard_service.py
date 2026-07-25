"""Per-quiz per-classroom leaderboard (Bảng vàng).

Ranking rule:
    1) best score_pct  DESC
    2) best time_taken_seconds  ASC  (tie-break)
    3) best submitted_at  ASC  (final tie-break)

Source of truth: QuizLog rows for the given (quiz_id, classroom_id).
Only students who are approved members of the classroom are ranked
(attempted but not member → still shown for completeness, with name
hydrated via ConsumerRepository).
"""
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from features.quiz.repositories.quiz_log_repository import QuizLogRepository
from features.quiz.repositories.quiz_attempt_repository import QuizAttemptRepository


def _safe_uuid(val):
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError):
        return None


def _hydrate_consumer(consumers, sid):
    try:
        c = consumers.find(sid)
    except Exception:
        c = None
    if c is None:
        return sid, ''
    return (
        getattr(c, 'full_name', '') or getattr(c, 'username', '') or sid,
        getattr(c, 'avatar_url', '') or '',
    )


def _best_per_student(rows):
    """Group log/attempt rows by student, keep the best attempt per the ranking rule."""
    by_student = defaultdict(list)
    for r in rows:
        by_student[str(r.student_id)].append(r)

    best = {}
    for sid, attempts in by_student.items():
        def keyfn(a):
            return (
                -int(getattr(a, 'score_pct', 0) or 0),
                int(getattr(a, 'time_taken_seconds', 0) or 0),
                getattr(a, 'submitted_at', datetime.max),
            )
        attempts_sorted = sorted(attempts, key=keyfn)
        best[sid] = attempts_sorted[0]
    return best


class QuizLeaderboardService:
    def __init__(self):
        self.log_repo = QuizLogRepository()
        self.attempt_repo = QuizAttemptRepository()

    def _all_rows(self, quiz_id, classroom_id):
        rows = []
        try:
            rows.extend(list(self.log_repo.get_by_classroom(quiz_id, classroom_id)))
        except Exception:
            pass
        try:
            rows.extend(list(self.attempt_repo.get_by_classroom(quiz_id, classroom_id)))
        except Exception:
            pass
        return rows

    def build(self, quiz_id, classroom_id, current_user_id=None, limit=20):
        from features.account.consumer.repositories import ConsumerRepository

        consumers = ConsumerRepository()
        rows = self._all_rows(quiz_id, classroom_id)
        best = _best_per_student(rows)

        entries = []
        for sid, a in best.items():
            name, avatar = _hydrate_consumer(consumers, sid)
            entries.append({
                'student_id': sid,
                'student_name': name,
                'student_avatar': avatar,
                'best_score_pct': int(getattr(a, 'score_pct', 0) or 0),
                'best_score': int(getattr(a, 'score', 0) or 0),
                'best_total_questions': int(getattr(a, 'total_questions', 0) or 0),
                'best_time_taken_seconds': int(getattr(a, 'time_taken_seconds', 0) or 0),
                'best_attempt_uid': str(getattr(a, 'uid', '')) if getattr(a, 'uid', None) else None,
                'best_attempt_number': int(getattr(a, 'attempt_number', 1) or 1),
                'best_submitted_at': getattr(a, 'submitted_at', None),
                'attempts_count': self._count_attempts(rows, sid),
            })

        entries.sort(key=lambda e: (
            -e['best_score_pct'],
            e['best_time_taken_seconds'],
            e['best_submitted_at'] or datetime.max,
        ))
        for i, e in enumerate(entries, start=1):
            e['rank'] = i

        total_students = len(entries)
        my_entry = None
        if current_user_id:
            cur = str(current_user_id)
            for e in entries:
                if e['student_id'] == cur:
                    my_entry = {
                        'rank': e['rank'],
                        'best_score_pct': e['best_score_pct'],
                        'best_time_taken_seconds': e['best_time_taken_seconds'],
                        'best_attempt_uid': e['best_attempt_uid'],
                        'attempts_count': e['attempts_count'],
                    }
                    break

        top3 = entries[:3]
        sliced = entries[:max(1, int(limit))]

        return {
            'quiz_id': str(quiz_id),
            'classroom_id': str(classroom_id),
            'total_students': total_students,
            'top_3': top3,
            'entries': sliced,
            'me': my_entry,
        }

    def student_detail(self, quiz_id, classroom_id, student_id):
        from features.account.consumer.repositories import ConsumerRepository

        consumers = ConsumerRepository()
        rows = self._all_rows(quiz_id, classroom_id)
        sid = str(student_id)

        attempts_for_student = [r for r in rows if str(r.student_id) == sid]
        if not attempts_for_student:
            name, avatar = _hydrate_consumer(consumers, sid)
            return {
                'student_id': sid,
                'student_name': name,
                'student_avatar': avatar,
                'rank': None,
                'best_score_pct': 0,
                'best_time_taken_seconds': 0,
                'best_attempt_uid': None,
                'attempts_count': 0,
                'attempts': [],
            }

        best = _best_per_student(attempts_for_student).get(sid)
        name, avatar = _hydrate_consumer(consumers, sid)

        attempt_payloads = []
        for a in attempts_for_student:
            attempt_payloads.append({
                'attempt_uid': str(getattr(a, 'uid', '')) if getattr(a, 'uid', None) else None,
                'attempt_number': int(getattr(a, 'attempt_number', 1) or 1),
                'score': int(getattr(a, 'score', 0) or 0),
                'total_questions': int(getattr(a, 'total_questions', 0) or 0),
                'score_pct': int(getattr(a, 'score_pct', 0) or 0),
                'time_taken_seconds': int(getattr(a, 'time_taken_seconds', 0) or 0),
                'submitted_at': getattr(a, 'submitted_at', None),
            })
        attempt_payloads.sort(key=lambda x: -x['score_pct'])

        full_lb = self.build(quiz_id=quiz_id, classroom_id=classroom_id, current_user_id=None, limit=1000)
        rank = None
        for e in full_lb.get('entries', []):
            if e['student_id'] == sid:
                rank = e['rank']
                break

        return {
            'student_id': sid,
            'student_name': name,
            'student_avatar': avatar,
            'rank': rank,
            'best_score_pct': int(getattr(best, 'score_pct', 0) or 0),
            'best_time_taken_seconds': int(getattr(best, 'time_taken_seconds', 0) or 0),
            'best_attempt_uid': str(getattr(best, 'uid', '')) if best and getattr(best, 'uid', None) else None,
            'attempts_count': len(attempt_payloads),
            'attempts': attempt_payloads,
        }

    def _count_attempts(self, rows, sid):
        return sum(1 for r in rows if str(r.student_id) == sid)
