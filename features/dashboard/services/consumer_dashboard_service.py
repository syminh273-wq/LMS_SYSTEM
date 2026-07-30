from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.services.base_service import BaseService
from features.calendar.repositories.attendance_repository import AttendanceRepository
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository
from features.course.classroom.repositories.classroom_member_repository import (
    ClassroomMemberRepository,
)
from features.course.classroom.repositories.classroom_repository import (
    Repository as ClassroomRepository,
)
from features.course.exam.repositories.exam_repositories import ExamRepository
from features.course.exam.repositories.exam_submission_repository import (
    ExamSubmissionRepository,
)
from features.quiz_collection.repositories.issued_certificate_repository import (
    IssuedCertificateRepository,
)
from features.quiz_collection.services.certificate_issuance_service import (
    CertificateIssuanceService,
)

_GPA_WEIGHTS = {'final': 3, 'midterm': 2, 'regular': 1}
_RECENT_LIMIT = 5


class ConsumerDashboardService(BaseService):
    """Single source of truth for the Consumer (student) dashboard."""

    def __init__(self) -> None:
        self.classroom_repo = ClassroomRepository()
        self.member_repo = ClassroomMemberRepository()
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.event_repo = CalendarEventRepository()
        self.attendance_repo = AttendanceRepository()
        self.issued_cert_repo = IssuedCertificateRepository()
        self.cert_issuance_service = CertificateIssuanceService()

    def get_summary(self, student_id) -> dict[str, Any]:
        classroom_uids = [m.classroom_uid for m in self.member_repo.get_by_member(student_id)]
        classrooms = {c.uid: c for c in self._load_classrooms(classroom_uids)}

        submissions = self._student_submissions(student_id, classroom_uids)
        graded = [s for s in submissions if s.status == 'graded' and s.grade is not None]

        return {
            'gpa': self._compute_gpa(graded),
            'active_classrooms': sum(1 for c in classrooms.values() if c.status == 'active'),
            'assignments_submitted': len(submissions),
            'assignments_total': self._count_assigned(classroom_uids),
            'attendance_pct': self._attendance_pct(student_id),
            'today_schedule': self._today_schedule(classroom_uids),
            'recent_grades': self._recent_grades(graded, classrooms),
            'recent_certificates': self._recent_certificates(student_id),
        }

    def _load_classrooms(self, classroom_uids):
        out = []
        for cid in classroom_uids:
            try:
                out.append(self.classroom_repo.find(cid))
            except Exception:
                continue
        return out

    def _student_submissions(self, student_id, classroom_uids):
        classroom_set = {str(c) for c in classroom_uids}
        rows = self.submission_repo.list_by_student(student_id)
        return [s for s in rows if str(s.classroom_id) in classroom_set]

    def _count_assigned(self, classroom_uids) -> int:
        total = 0
        for cid in classroom_uids:
            total += len(self.exam_repo.list_published_by_classroom(cid))
        return total

    def _compute_gpa(self, graded_submissions) -> dict[str, Any]:
        """Weighted average: final x3, midterm x2, regular x1, scaled to /4.0."""
        if not graded_submissions:
            return {'gpa_4': 0.0, 'avg_10': 0.0}

        exam_cache: dict[str, Any] = {}
        weighted_sum = 0.0
        weight_total = 0.0
        for sub in graded_submissions:
            exam_key = str(sub.exam_id)
            if exam_key not in exam_cache:
                exam_cache[exam_key] = self.exam_repo.get_by_uid(sub.exam_id)
            exam = exam_cache[exam_key]

            period = getattr(exam, 'exam_period', 'regular') if exam else 'regular'
            weight = _GPA_WEIGHTS.get(period, 1)
            max_grade = sub.max_grade or 10.0
            normalized_10 = (sub.grade / max_grade) * 10 if max_grade else 0.0

            weighted_sum += normalized_10 * weight
            weight_total += weight

        avg_10 = weighted_sum / weight_total if weight_total else 0.0
        gpa_4 = avg_10 / 10 * 4
        return {'gpa_4': round(gpa_4, 2), 'avg_10': round(avg_10, 2)}

    def _attendance_pct(self, student_id) -> float:
        rows = list(self.attendance_repo.filter(user_id=student_id))
        if not rows:
            return 0.0
        present = sum(1 for r in rows if r.status == 'present')
        return round((present / len(rows)) * 100, 1)

    def _today_schedule(self, classroom_uids) -> list[Any]:
        if not classroom_uids:
            return []
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        events = self.event_repo.get_by_classroom_uids_in_range(classroom_uids, start, end)
        events.sort(key=lambda e: e.start_time)
        return events

    def _recent_grades(self, graded_submissions, classrooms) -> list[dict[str, Any]]:
        rows = sorted(
            graded_submissions,
            key=lambda s: s.graded_at or s.submitted_at,
            reverse=True,
        )[:_RECENT_LIMIT]

        out = []
        for sub in rows:
            exam = self.exam_repo.get_by_uid(sub.exam_id)
            classroom = classrooms.get(sub.classroom_id)
            max_grade = sub.max_grade or 10.0
            out.append({
                'submission_uid': str(sub.uid),
                'exam_title': getattr(exam, 'title', ''),
                'classroom_name': getattr(classroom, 'name', ''),
                'grade': sub.grade,
                'max_grade': max_grade,
                'percent': round((sub.grade / max_grade) * 100, 1) if max_grade else 0.0,
                'graded_at': sub.graded_at or sub.submitted_at,
            })
        return out

    def _recent_certificates(self, student_id) -> list[dict[str, Any]]:
        certs = self.issued_cert_repo.get_by_student(student_id)
        certs = sorted(certs, key=lambda c: c.issued_at, reverse=True)[:_RECENT_LIMIT]
        return self.cert_issuance_service.enrich_issued_certificates(certs)
