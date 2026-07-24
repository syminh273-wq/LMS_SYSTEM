"""Build a unified per-classroom leaderboard that combines:

    - Gamification (XP / level / streak) from `features.ranking`
    - Academic score (quiz/exam/attendance) from `features.course.classroom`

The two source-of-truth services are kept intact per the spec
(`docs/features/ranking/specs/overview.md`). This service only
aggregates their output and enriches each row with a human-readable
`explanation` string.
"""
import logging
from uuid import UUID

from features.account.consumer.repositories import ConsumerRepository
from features.ranking.repositories.student_xp_repository import StudentXPRepository
from features.ranking.services.explanation_resolver import (
    explain_score,
    explain_xp_level,
)
from features.ranking.services.level_service import level_title

logger = logging.getLogger(__name__)


def _safe_uuid(val):
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError):
        return None


class UnifiedLeaderboardService:
    def __init__(self):
        self.xp_repo = StudentXPRepository()
        self.consumers = ConsumerRepository()

    def _hydrate_profile(self, student_id: str):
        try:
            c = self.consumers.find(student_id)
        except Exception:
            c = None
        if c is None:
            return student_id, ''
        return (
            getattr(c, 'full_name', '') or getattr(c, 'username', '') or student_id,
            getattr(c, 'avatar_url', '') or '',
        )

    def _xp_entry(self, student_id: str) -> dict:
        try:
            row = self.xp_repo.get(_safe_uuid(student_id))
        except Exception:
            row = None
        if row is None:
            return {
                'total_xp': 0,
                'level': 1,
                'level_title': level_title(1),
            }
        total_xp = int(getattr(row, 'total_xp', 0) or 0)
        level = int(getattr(row, 'level', 1) or 1)
        return {
            'total_xp': total_xp,
            'level': level,
            'level_title': level_title(level),
        }

    def build_for_classroom(self, classroom_id, current_user_id=None, limit=10):
        """Return unified leaderboard rows for one classroom.

        Each entry contains BOTH:
            - XP / level (from ranking module)
            - academic score (from classroom.leaderboard module)
            - explanation (human-readable Vietnamese)
        """
        from features.course.classroom.services.leaderboard_service import LeaderboardService
        from features.course.classroom.repositories.classroom_member_repository import (
            ClassroomMemberRepository,
        )

        cid = str(classroom_id) if classroom_id else None
        if not cid:
            return {
                'classroom_uid': '',
                'total_students': 0,
                'my_rank': None,
                'my_score': None,
                'my_xp': 0,
                'entries': [],
            }

        try:
            members = list(ClassroomMemberRepository().get_members(cid))
        except Exception as exc:
            logger.warning(f"[UnifiedLB] get_members failed: {exc}")
            members = []
        member_ids = [str(m.member_id) for m in members]

        score_payload = {}
        try:
            score_data = LeaderboardService().build(
                classroom_id=cid,
                current_user_id=str(current_user_id) if current_user_id else None,
                limit=max(1, int(limit)),
            )
            for e in score_data.get('entries', []):
                score_payload[str(e.get('student_id'))] = e
        except Exception as exc:
            logger.warning(f"[UnifiedLB] score build failed: {exc}")

        rows = []
        for sid in member_ids:
            name, avatar = self._hydrate_profile(sid)
            xp = self._xp_entry(sid)
            sc = score_payload.get(sid, {})
            quiz_avg = float(sc.get('quiz_avg', 0) or 0)
            exam_avg = float(sc.get('exam_avg', 0) or 0)
            attendance_pct = float(sc.get('attendance_pct', 0) or 0)
            total_score = float(sc.get('total_score', 0) or 0)
            rows.append({
                'student_id': sid,
                'student_name': name,
                'student_avatar': avatar,
                'total_xp': xp['total_xp'],
                'level': xp['level'],
                'level_title': xp['level_title'],
                'total_score': total_score,
                'quiz_avg': quiz_avg,
                'exam_avg': exam_avg,
                'quiz_count': int(sc.get('quiz_count', 0) or 0),
                'exam_count': int(sc.get('exam_count', 0) or 0),
                'attendance_pct': attendance_pct,
            })

        rows.sort(
            key=lambda r: (
                -r['total_score'],
                -r['total_xp'],
                r['student_id'],
            )
        )
        for i, row in enumerate(rows, start=1):
            row['rank'] = i
            row['explanation'] = (
                f"{explain_xp_level(row['level'], row['total_xp'])}. "
                f"{explain_score(row['quiz_avg'], row['exam_avg'], row['attendance_pct'])}. "
                f"Tổng điểm: {round(row['total_score'], 2)}."
            )

        total_students = len(rows)
        my_rank = None
        my_score = None
        my_xp = 0
        if current_user_id:
            cur = str(current_user_id)
            for row in rows:
                if row['student_id'] == cur:
                    my_rank = row['rank']
                    my_score = row['total_score']
                    my_xp = row['total_xp']
                    break

        return {
            'classroom_uid': cid,
            'total_students': total_students,
            'my_rank': my_rank,
            'my_score': my_score,
            'my_xp': my_xp,
            'entries': rows[: max(1, int(limit))],
        }

    def build_for_student(self, student_id, classroom_id):
        """Return one student's stats in one classroom (XP + Score + explanation)."""
        from features.course.classroom.services.leaderboard_service import LeaderboardService

        sid = str(student_id) if student_id else None
        cid = str(classroom_id) if classroom_id else None
        if not sid or not cid:
            return {
                'student_id': sid or '',
                'classroom_uid': cid or '',
                'rank': None,
                'total_xp': 0,
                'level': 1,
                'level_title': level_title(1),
                'total_score': 0.0,
                'quiz_avg': 0.0,
                'exam_avg': 0.0,
                'quiz_count': 0,
                'exam_count': 0,
                'attendance_pct': 0.0,
                'explanation': '',
            }

        lb = self.build_for_classroom(
            classroom_id=cid, current_user_id=sid, limit=1000
        )
        match = next(
            (e for e in lb.get('entries', []) if str(e.get('student_id')) == sid),
            None,
        )
        if match is None:
            name, avatar = self._hydrate_profile(sid)
            xp = self._xp_entry(sid)
            explanation = (
                f"{explain_xp_level(xp['level'], xp['total_xp'])}. "
                "Chưa có dữ liệu điểm thành tích trong lớp này."
            )
            return {
                'student_id': sid,
                'classroom_uid': cid,
                'student_name': name,
                'student_avatar': avatar,
                'rank': None,
                'total_xp': xp['total_xp'],
                'level': xp['level'],
                'level_title': xp['level_title'],
                'total_score': 0.0,
                'quiz_avg': 0.0,
                'exam_avg': 0.0,
                'quiz_count': 0,
                'exam_count': 0,
                'attendance_pct': 0.0,
                'explanation': explanation,
            }
        return {
            'student_id': match['student_id'],
            'classroom_uid': cid,
            'student_name': match['student_name'],
            'student_avatar': match['student_avatar'],
            'rank': match['rank'],
            'total_xp': match['total_xp'],
            'level': match['level'],
            'level_title': match['level_title'],
            'total_score': match['total_score'],
            'quiz_avg': match['quiz_avg'],
            'exam_avg': match['exam_avg'],
            'quiz_count': match['quiz_count'],
            'exam_count': match['exam_count'],
            'attendance_pct': match['attendance_pct'],
            'explanation': match['explanation'],
        }
