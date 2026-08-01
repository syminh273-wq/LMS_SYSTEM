import logging
from collections import defaultdict

from features.account.consumer.repositories import ConsumerRepository
from features.ranking.services.explanation_resolver import explain_score
from core.services.base_service import BaseService

logger = logging.getLogger(__name__)

EXAM_PERIOD_WEIGHTS = {'final': 3, 'midterm': 2, 'regular': 1}
DEFAULT_EXAM_WEIGHT = 1


class UnifiedLeaderboardService(BaseService):
    def __init__(self):
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

    def _score_by_student(self, classroom_id):
        """Return {student_id: (weighted_avg_score_pct, graded_submission_count)}.

        Score per submission = grade / max_grade * 100, weighted by the
        parent exam's `exam_period` (final x3, midterm x2, regular x1).
        """
        from features.course.exam.repositories.exam_repositories import ExamRepository
        from features.course.exam.repositories.exam_submission_repository import (
            ExamSubmissionRepository,
        )

        try:
            exams = ExamRepository().list_by_classroom(classroom_id)
        except Exception as exc:
            logger.warning(f"[UnifiedLB] list_by_classroom failed: {exc}")
            exams = []
        period_by_exam = {str(e.uid): getattr(e, 'exam_period', 'regular') for e in exams}

        try:
            submissions = ExamSubmissionRepository().iter_by_classroom(classroom_id)
        except Exception as exc:
            logger.warning(f"[UnifiedLB] iter_by_classroom failed: {exc}")
            submissions = []

        weighted_sum = defaultdict(float)
        weight_sum = defaultdict(float)
        count = defaultdict(int)
        for s in submissions:
            grade = getattr(s, 'grade', None)
            max_grade = getattr(s, 'max_grade', None) or 10
            if grade is None or max_grade <= 0:
                continue
            sid = str(s.student_id)
            period = period_by_exam.get(str(s.exam_id), 'regular')
            weight = EXAM_PERIOD_WEIGHTS.get(period, DEFAULT_EXAM_WEIGHT)
            score_pct = (float(grade) / float(max_grade)) * 100.0
            weighted_sum[sid] += score_pct * weight
            weight_sum[sid] += weight
            count[sid] += 1

        return {
            sid: (round(weighted_sum[sid] / weight_sum[sid], 2), count[sid])
            for sid in weight_sum
        }

    def build_for_classroom(self, classroom_id, current_user_id=None, limit=10):
        """Return the academic score board for one classroom.

        Each entry: rank, student profile, weighted exam score, and a
        human-readable `explanation`.
        """
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
                'entries': [],
            }

        try:
            members = list(ClassroomMemberRepository().get_members(cid))
        except Exception as exc:
            logger.warning(f"[UnifiedLB] get_members failed: {exc}")
            members = []
        member_ids = [str(m.member_id) for m in members]

        score_by_student = self._score_by_student(cid)

        rows = []
        for sid in member_ids:
            name, avatar = self._hydrate_profile(sid)
            total_score, exam_count = score_by_student.get(sid, (0.0, 0))
            rows.append({
                'student_id': sid,
                'student_name': name,
                'student_avatar': avatar,
                'total_score': total_score,
                'exam_count': exam_count,
            })

        rows.sort(key=lambda r: (-r['total_score'], r['student_id']))
        for i, row in enumerate(rows, start=1):
            row['rank'] = i
            row['explanation'] = explain_score(row['total_score'], row['exam_count'])

        total_students = len(rows)
        my_rank = None
        my_score = None
        if current_user_id:
            cur = str(current_user_id)
            for row in rows:
                if row['student_id'] == cur:
                    my_rank = row['rank']
                    my_score = row['total_score']
                    break

        return {
            'classroom_uid': cid,
            'total_students': total_students,
            'my_rank': my_rank,
            'my_score': my_score,
            'entries': rows[: max(1, int(limit))],
        }

    def build_for_student(self, student_id, classroom_id):
        """Return one student's academic score in one classroom."""
        sid = str(student_id) if student_id else None
        cid = str(classroom_id) if classroom_id else None
        if not sid or not cid:
            return {
                'student_id': sid or '',
                'classroom_uid': cid or '',
                'rank': None,
                'total_score': 0.0,
                'exam_count': 0,
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
            return {
                'student_id': sid,
                'classroom_uid': cid,
                'student_name': name,
                'student_avatar': avatar,
                'rank': None,
                'total_score': 0.0,
                'exam_count': 0,
                'explanation': 'Chưa có dữ liệu điểm thành tích trong lớp này.',
            }
        return {
            'student_id': match['student_id'],
            'classroom_uid': cid,
            'student_name': match['student_name'],
            'student_avatar': match['student_avatar'],
            'rank': match['rank'],
            'total_score': match['total_score'],
            'exam_count': match['exam_count'],
            'explanation': match['explanation'],
        }
