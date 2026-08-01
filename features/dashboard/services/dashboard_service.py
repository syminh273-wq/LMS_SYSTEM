from __future__ import annotations

from typing import Any

from features.course.classroom.repositories.classroom_member_repository import (
    ClassroomMemberRepository,
)
from features.course.classroom.repositories.classroom_repository import (
    ClassroomRepository,
)
from features.course.exam.repositories.exam_repositories import ExamRepository
from features.course.exam.repositories.exam_submission_repository import (
    ExamSubmissionRepository,
)
from features.quiz_collection.repositories.issued_certificate_repository import (
    IssuedCertificateRepository,
)
from core.services.base_service import BaseService


class DashboardService(BaseService):
    """Single source of truth for the Space dashboard."""

    def __init__(self) -> None:
        self.classroom_repo = ClassroomRepository()
        self.member_repo = ClassroomMemberRepository()
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.issued_cert_repo = IssuedCertificateRepository()

    def get_summary(self, teacher_id) -> dict[str, Any]:
        classrooms = list(self.classroom_repo.get_by_teacher(teacher_id))
        classroom_uids = [c.uid for c in classrooms]

        kpis = self._compute_kpis(classrooms, classroom_uids)
        top_classes = self._compute_top_classes(classrooms)

        return {
            'kpis': kpis,
            'top_classes': top_classes,
        }

    def _compute_kpis(self, classrooms, classroom_uids) -> dict[str, Any]:
        active_classrooms = [c for c in classrooms if c.status == 'active']

        total_students = 0
        for cid in classroom_uids:
            members = self.member_repo.get_members(cid)
            total_students += sum(1 for m in members if m.role == 'student')

        certificates_issued = self._count_certificates(classroom_uids)
        submissions, graded = self._submission_stats(classroom_uids)
        exams_published = self._count_published_exams(classroom_uids)

        completion_rate = 0.0
        if exams_published and total_students:
            completion_rate = round(min(100.0, (submissions / max(1, exams_published * total_students)) * 100), 1)

        return {
            'total_classrooms': len(classrooms),
            'active_classrooms': len(active_classrooms),
            'total_students': total_students,
            'completion_rate_pct': completion_rate,
            'certificates_issued': certificates_issued,
            'exams_published': exams_published,
            'submissions': submissions,
            'graded': graded,
        }

    def _count_certificates(self, classroom_uids) -> int:
        total = 0
        for cid in classroom_uids:
            rows = list(
                self.issued_cert_repo.model.objects(classroom_id=cid, is_deleted=False).allow_filtering()
            )
            total += len(rows)
        return total

    def _submission_stats(self, classroom_uids) -> tuple[int, int]:
        submissions = 0
        graded = 0
        for cid in classroom_uids:
            for sub in self.submission_repo.iter_by_classroom(cid):
                submissions += 1
                if sub.status == 'graded':
                    graded += 1
        return submissions, graded

    def _count_published_exams(self, classroom_uids) -> int:
        total = 0
        for cid in classroom_uids:
            total += len(self.exam_repo.list_published_by_classroom(cid))
        return total

    def _compute_top_classes(self, classrooms) -> list[dict[str, Any]]:
        scored = []
        for c in classrooms:
            members = list(self.member_repo.get_members(c.uid))
            students = [m for m in members if m.role == 'student']
            submissions = sum(1 for _ in self.submission_repo.iter_by_classroom(c.uid))
            max_students = max(1, c.max_students or 0)
            progress = round(min(100, (len(students) / max_students) * 100), 0)
            scored.append({
                'uid': str(c.uid),
                'name': c.name,
                'students': len(students),
                'max': c.max_students or 0,
                'submissions': submissions,
                'progress': int(progress),
            })

        scored.sort(key=lambda x: (x['students'], x['submissions']), reverse=True)
        return scored[:5]
