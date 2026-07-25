"""Aggregate dashboard data for a space (teacher) account.

Pulls KPIs, weekly trend, top classes, and recent activity in a single
round-trip so the frontend can render the Space dashboard with one
HTTP request instead of N.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from features.course.classroom.repositories.classroom_member_repository import (
    ClassroomMemberRepository,
)
from features.course.classroom.repositories.classroom_repository import (
    Repository as ClassroomRepository,
)
from features.course.classroom.services.classroom_activity_log_service import (
    ClassroomActivityLogService,
)
from features.course.exam.repositories.exam_repositories import ExamRepository
from features.course.exam.repositories.exam_submission_repository import (
    ExamSubmissionRepository,
)
from features.quiz_collection.repositories.issued_certificate_repository import (
    IssuedCertificateRepository,
)

logger = logging.getLogger(__name__)

_ENROLL_EVENTS = {'member_joined', 'member_approved'}
_SUBMIT_EVENTS = {'exam_submitted', 'exam_opened'}
_WEEKDAY_KEYS = ['day_mon', 'day_tue', 'day_wed', 'day_thu', 'day_fri', 'day_sat', 'day_sun']


class DashboardService:
    """Single source of truth for the Space dashboard."""

    def __init__(self) -> None:
        self.classroom_repo = ClassroomRepository()
        self.member_repo = ClassroomMemberRepository()
        self.activity_service = ClassroomActivityLogService()
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.issued_cert_repo = IssuedCertificateRepository()

    # ── Public API ─────────────────────────────────────────────────────────
    def get_summary(self, teacher_id) -> dict[str, Any]:
        teacher_id = self._as_uuid(teacher_id)

        classrooms = list(self.classroom_repo.get_by_teacher(teacher_id))
        classroom_uids = [c.uid for c in classrooms]

        kpis = self._compute_kpis(teacher_id, classrooms, classroom_uids)
        weekly_trend = self._compute_weekly_trend(classroom_uids)
        top_classes = self._compute_top_classes(classrooms)
        recent_activity = self._compute_recent_activity(classroom_uids)

        return {
            'kpis': kpis,
            'weekly_trend': weekly_trend,
            'top_classes': top_classes,
            'recent_activity': recent_activity,
        }

    def get_usage(self, teacher_id) -> dict[str, Any]:
        teacher_id = self._as_uuid(teacher_id)
        classrooms = list(self.classroom_repo.get_by_teacher(teacher_id))
        classroom_uids = [c.uid for c in classrooms]

        exams = []
        for cid in classroom_uids:
            exams.extend(self.exam_repo.list_by_classroom(cid))

        published_exams = [e for e in exams if e.status in ('published', 'ongoing', 'closed')]

        return {
            'storage_used_mb': self._estimate_storage_mb(teacher_id),
            'storage_limit_mb': 5120,
            'api_calls_this_month': self._estimate_api_calls(teacher_id),
            'api_calls_limit': 10000,
            'active_classrooms': len([c for c in classrooms if getattr(c, 'status', 'active') == 'active']),
            'total_classrooms': len(classrooms),
            'published_exams': len(published_exams),
        }

    # ── KPIs ───────────────────────────────────────────────────────────────
    def _compute_kpis(self, teacher_id, classrooms, classroom_uids) -> dict[str, Any]:
        active_classrooms = [c for c in classrooms if getattr(c, 'status', 'active') == 'active']

        total_students = 0
        for cid in classroom_uids:
            members = self.member_repo.get_members(cid)
            total_students += sum(1 for m in members if getattr(m, 'role', 'student') == 'student')

        certificates_issued = self._count_certificates(teacher_id, classroom_uids)
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

    def _count_certificates(self, teacher_id, classroom_uids) -> int:
        try:
            try:
                rows = list(
                    self.issued_cert_repo.model.objects(issued_by=teacher_id, is_deleted=False)
                )
                return len(rows)
            except Exception:
                total = 0
                for cid in classroom_uids:
                    rows = list(
                        self.issued_cert_repo.model.objects(classroom_id=cid, is_deleted=False).allow_filtering()
                    )
                    total += len(rows)
                return total
        except Exception as exc:
            logger.warning('[dashboard] _count_certificates failed: %s', exc)
            return 0

    def _submission_stats(self, classroom_uids) -> tuple[int, int]:
        submissions = 0
        graded = 0
        for cid in classroom_uids:
            for sub in self.submission_repo.iter_by_classroom(cid):
                submissions += 1
                if getattr(sub, 'status', '') == 'graded':
                    graded += 1
        return submissions, graded

    def _count_published_exams(self, classroom_uids) -> int:
        total = 0
        for cid in classroom_uids:
            total += len(self.exam_repo.list_published_by_classroom(cid))
        return total

    # ── Weekly trend (last 7 days, Mon→Sun) ────────────────────────────────
    def _compute_weekly_trend(self, classroom_uids) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        days = [monday + timedelta(days=i) for i in range(7)]

        enrolled_per_day: dict[str, int] = {d.isoformat(): 0 for d in days}
        submitted_per_day: dict[str, int] = {d.isoformat(): 0 for d in days}

        for cid in classroom_uids:
            logs = self.activity_service.list(cid, log_level=None, limit=400)
            for log in logs:
                created = log.get('created_at')
                if not created:
                    continue
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00')).astimezone(timezone.utc).date()
                except Exception:
                    continue
                if dt < monday or dt > today:
                    continue
                key = dt.isoformat()
                if key not in enrolled_per_day:
                    continue
                event = log.get('event_type')
                if event in _ENROLL_EVENTS:
                    enrolled_per_day[key] += 1
                elif event in _SUBMIT_EVENTS:
                    submitted_per_day[key] += 1

        return [
            {
                'date': d.isoformat(),
                'weekday': _WEEKDAY_KEYS[i],
                'enrolled': enrolled_per_day[d.isoformat()],
                'submitted': submitted_per_day[d.isoformat()],
            }
            for i, d in enumerate(days)
        ]

    # ── Top classes (by student count) ─────────────────────────────────────
    def _compute_top_classes(self, classrooms) -> list[dict[str, Any]]:
        scored = []
        for c in classrooms:
            members = list(self.member_repo.get_members(c.uid))
            students = [m for m in members if getattr(m, 'role', 'student') == 'student']
            submissions = sum(1 for _ in self.submission_repo.iter_by_classroom(c.uid))
            max_students = max(1, int(getattr(c, 'max_students', 0) or 0))
            progress = round(min(100, (len(students) / max_students) * 100), 0)
            scored.append({
                'uid': str(c.uid),
                'name': getattr(c, 'name', ''),
                'students': len(students),
                'max': int(getattr(c, 'max_students', 0) or 0),
                'submissions': submissions,
                'progress': int(progress),
            })

        scored.sort(key=lambda x: (x['students'], x['submissions']), reverse=True)
        return scored[:5]

    # ── Recent activity (merge across all classrooms) ─────────────────────
    def _compute_recent_activity(self, classroom_uids) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for cid in classroom_uids:
            merged.extend(self.activity_service.list(cid, log_level='major', limit=15))

        merged.sort(
            key=lambda x: (x.get('created_at') or ''),
            reverse=True,
        )
        return merged[:10]

    # ── Storage / API usage (best-effort estimates) ────────────────────────
    def _estimate_storage_mb(self, teacher_id) -> int:
        try:
            from features.resource.repositories.resource_repository import ResourceRepository
            repo = ResourceRepository()
            total_bytes = 0
            for r in repo.get_by_owner(teacher_id):
                total_bytes += int(getattr(r, 'size', 0) or 0)
            return round(total_bytes / (1024 * 1024))
        except Exception:
            return 0

    def _estimate_api_calls(self, teacher_id) -> int:
        try:
            from features.payment.repositories.payment_repository import PaymentRepository
            repo = PaymentRepository()
            return len(list(repo.get_by_teacher(teacher_id, limit=200)))
        except Exception:
            return 0

    # ── Helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _as_uuid(value) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
