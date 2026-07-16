import logging
import secrets
import string
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from features.quiz_collection.repositories import (
    QuizCollectionRepository,
    QuizCollectionItemRepository,
    QuizCollectionAssignmentRepository,
    CertificateRepository,
    IssuedCertificateRepository,
)

logger = logging.getLogger(__name__)

_VERIFICATION_ALPHABET = string.ascii_uppercase + string.digits

DEFAULT_PASSING_SCORE_PCT = 50
DEFAULT_MAX_ATTEMPTS = 0
DEFAULT_TIME_LIMIT_SECONDS = 0
DEFAULT_SHOW_EXPLANATION = True
DEFAULT_SHUFFLE_QUESTIONS = False
DEFAULT_SHUFFLE_OPTIONS = False


def _generate_verification_code(length: int = 12) -> str:
    return ''.join(secrets.choice(_VERIFICATION_ALPHABET) for _ in range(length))


def _is_student_in_classroom(student_id, classroom_id) -> bool:
    try:
        from features.course.classroom.repositories.classroom_member_repository import (
            ClassroomMemberRepository,
        )
        repo = ClassroomMemberRepository()
        return repo.is_member(classroom_id, student_id)
    except Exception as exc:
        logger.warning(f"[Certificate] Membership check failed for student={student_id} classroom={classroom_id}: {exc}")
        return False


def _ensure_quiz_assignment(quiz_id, classroom_id, collection) -> None:
    """
    Idempotent fallback: if a quiz is part of a collection assigned to a classroom
    but no `quiz_assignments` row exists yet (missing seed / broken workflow),
    create one with safe defaults so certificate issuance can proceed.

    This does NOT bypass any teacher config — if an assignment already exists, it
    is left untouched. The defaults match what the rest of the system uses when
    an assignment is missing.
    """
    try:
        from features.quiz.repositories.quiz_assignment_repository import (
            QuizAssignmentRepository,
        )
        repo = QuizAssignmentRepository()
        existing = repo.find_assignment(quiz_id, classroom_id)
        if existing:
            return

        assigned_by = getattr(collection, 'created_by', None)
        if not assigned_by:
            return

        logger.info(
            f"[Certificate] Auto-creating missing quiz_assignment for "
            f"quiz={quiz_id} classroom={classroom_id} (collection={collection.uid})"
        )
        repo.assign(
            quiz_id=quiz_id,
            classroom_id=classroom_id,
            assigned_by=assigned_by,
            passing_score_pct=DEFAULT_PASSING_SCORE_PCT,
            max_attempts=DEFAULT_MAX_ATTEMPTS,
            time_limit_seconds=DEFAULT_TIME_LIMIT_SECONDS,
            show_explanation=DEFAULT_SHOW_EXPLANATION,
            shuffle_questions=DEFAULT_SHUFFLE_QUESTIONS,
            shuffle_options=DEFAULT_SHUFFLE_OPTIONS,
        )
    except Exception as exc:
        logger.warning(
            f"[Certificate] Could not auto-create quiz_assignment for "
            f"quiz={quiz_id} classroom={classroom_id}: {exc}"
        )


class CertificateIssuanceService:
    """
    Decides whether a student who just submitted a quiz has now completed a
    QuizCollection, and if so, issues a certificate (idempotent).
    """

    def __init__(self):
        self.collection_repo = QuizCollectionRepository()
        self.item_repo = QuizCollectionItemRepository()
        self.assignment_repo = QuizCollectionAssignmentRepository()
        self.certificate_repo = CertificateRepository()
        self.issued_repo = IssuedCertificateRepository()

    def check_and_issue(self, student_id, classroom_id, just_submitted_quiz_id=None):
        """
        Idempotent certificate issuance.

        If `just_submitted_quiz_id` is provided, only collections containing
        that quiz are considered (cheaper, used right after a submit).
        If it is None, every collection assigned to the classroom is checked
        (used by lazy / self-healing paths).
        """
        from features.quiz_collection.services.notification_service_helper import notify_issued

        if not _is_student_in_classroom(student_id, classroom_id):
            logger.warning(
                f"[Certificate] Refusing issuance: student={student_id} is not an "
                f"approved member of classroom={classroom_id}."
            )
            return []

        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        if not assignments:
            return []

        issued_now = []
        for assignment in assignments:
            collection_id = str(assignment.collection_id)
            try:
                collection = self.collection_repo.find(collection_id)
            except Exception as exc:
                logger.warning(f"[Certificate] Could not load collection {collection_id}: {exc}")
                continue

            if just_submitted_quiz_id is not None:
                if str(just_submitted_quiz_id) not in self.item_repo.get_quiz_ids(collection_id):
                    continue

            self._ensure_all_quiz_assignments(collection_id, classroom_id, collection)

            if not self._is_completed(collection_id, classroom_id, student_id):
                continue

            if self.issued_repo.exists(collection_id, classroom_id, student_id):
                continue

            certificate_id = collection.certificate_id
            if not certificate_id:
                logger.info(
                    f"[Certificate] Collection {collection_id} completed by student {student_id} "
                    f"but no certificate assigned. Skipping issuance."
                )
                continue

            try:
                issued = self.issued_repo.create(
                    student_id=student_id,
                    certificate_id=certificate_id,
                    collection_id=collection_id,
                    classroom_id=classroom_id,
                    issued_by=str(collection.created_by),
                    verification_code=_generate_verification_code(),
                )
            except Exception as exc:
                logger.exception(
                    f"[Certificate] Failed to create IssuedCertificate "
                    f"student={student_id} classroom={classroom_id} collection={collection_id}: {exc}"
                )
                continue
            issued_now.append(issued)
            logger.info(
                f"[Certificate] Issued certificate {issued.uid} "
                f"to student={student_id} collection={collection_id} classroom={classroom_id}."
            )

            try:
                notify_issued(student_id, collection, issued)
            except Exception as exc:
                logger.warning(f"[Certificate] Notification failed: {exc}")

        return issued_now

    def _ensure_all_quiz_assignments(self, collection_id, classroom_id, collection) -> None:
        """Make sure every quiz in the collection has a quiz_assignments row."""
        try:
            quiz_ids = self.item_repo.get_quiz_ids(collection_id)
        except Exception as exc:
            logger.warning(f"[Certificate] Could not list quiz items for {collection_id}: {exc}")
            return
        for quiz_id in quiz_ids:
            _ensure_quiz_assignment(quiz_id, classroom_id, collection)

    def _is_completed(self, collection_id, classroom_id, student_id) -> bool:
        from features.quiz.repositories.quiz_log_repository import QuizLogRepository
        from features.quiz.repositories.quiz_assignment_repository import QuizAssignmentRepository

        quiz_ids = self.item_repo.get_quiz_ids(collection_id)
        if not quiz_ids:
            return False

        log_repo = QuizLogRepository()
        assignment_repo = QuizAssignmentRepository()

        for quiz_id in quiz_ids:
            assignment = assignment_repo.find_assignment(quiz_id, classroom_id)
            if not assignment:
                return False
            passing = assignment.passing_score_pct or DEFAULT_PASSING_SCORE_PCT

            logs = list(
                log_repo.get_by_student(quiz_id, classroom_id, student_id)
                .order_by('-submitted_at')
            )
            if not logs:
                return False
            best = max(logs, key=lambda l: l.score_pct or 0)
            if (best.score_pct or 0) < passing:
                return False

        return True

    def get_student_progress(self, collection_id, classroom_id, student_id) -> dict:
        from features.quiz.repositories.quiz_assignment_repository import QuizAssignmentRepository

        try:
            collection = self.collection_repo.find(collection_id)
        except Exception:
            collection = None

        quiz_ids = self.item_repo.get_quiz_ids(collection_id)
        total = len(quiz_ids)
        if total == 0:
            return {
                'total': 0,
                'passed': 0,
                'is_completed': False,
                'percent': 0,
                'passed_quiz_ids': [],
                'missing_quiz_ids': [],
            }

        if collection is not None:
            self._ensure_all_quiz_assignments(collection_id, classroom_id, collection)

        from features.quiz.repositories.quiz_log_repository import QuizLogRepository

        log_repo = QuizLogRepository()
        assignment_repo = QuizAssignmentRepository()

        passed_quiz_ids = []
        for quiz_id in quiz_ids:
            assignment = assignment_repo.find_assignment(quiz_id, classroom_id)
            if not assignment:
                continue
            passing = assignment.passing_score_pct or DEFAULT_PASSING_SCORE_PCT
            logs = list(
                log_repo.get_by_student(quiz_id, classroom_id, student_id)
            )
            if not logs:
                continue
            best = max(logs, key=lambda l: l.score_pct or 0)
            if (best.score_pct or 0) >= passing:
                passed_quiz_ids.append(quiz_id)

        passed = len(passed_quiz_ids)
        percent = round((passed / total) * 100, 1) if total else 0
        is_completed = passed == total

        result = {
            'total': total,
            'passed': passed,
            'is_completed': is_completed,
            'percent': percent,
            'passed_quiz_ids': passed_quiz_ids,
            'missing_quiz_ids': [q for q in quiz_ids if q not in passed_quiz_ids],
        }

        if is_completed:
            try:
                existing = self.issued_repo.find_for_collection_classroom_student(
                    collection_id, classroom_id, student_id
                )
                if not existing:
                    logger.info(
                        f"[Certificate] Lazy issuance triggered by progress read: "
                        f"student={student_id} collection={collection_id} classroom={classroom_id}."
                    )
                    self.check_and_issue(
                        student_id=student_id,
                        classroom_id=classroom_id,
                        just_submitted_quiz_id=None,
                    )
            except Exception as exc:
                logger.warning(
                    f"[Certificate] Lazy issuance during progress read failed: {exc}"
                )

        return result

    # ------------------------------------------------------------------
    # Enriched response helpers
    # ------------------------------------------------------------------
    def enrich_issued_certificate(self, issued) -> dict:
        """
        Convert an IssuedCertificate model into a response-friendly dict with
        resolved template title, collection title, student name, classroom name,
        and human-readable issued_at string.
        """
        return self.enrich_issued_certificates([issued])[0]

    def enrich_issued_certificates(self, issued_list) -> List[dict]:
        """
        Batch enrichment: resolve all referenced collections, certificates,
        consumers, classrooms in a small number of lookups.
        """
        if not issued_list:
            return []

        cert_ids = set()
        coll_ids = set()
        student_ids = set()
        classroom_ids = set()
        for it in issued_list:
            try:
                if it.certificate_id:
                    cert_ids.add(UUID(str(it.certificate_id)))
            except Exception:
                pass
            try:
                if it.collection_id:
                    coll_ids.add(UUID(str(it.collection_id)))
            except Exception:
                pass
            try:
                if it.student_id:
                    student_ids.add(UUID(str(it.student_id)))
            except Exception:
                pass
            try:
                if it.classroom_id:
                    classroom_ids.add(UUID(str(it.classroom_id)))
            except Exception:
                pass

        certs_map = self._safe_fetch_certificates(cert_ids)
        colls_map = self._safe_fetch_collections(coll_ids)
        students_map = self._safe_fetch_consumers(student_ids)
        classrooms_map = self._safe_fetch_classrooms(classroom_ids)

        enriched = []
        for it in issued_list:
            cert_uid = self._safe_uuid(it.certificate_id)
            coll_uid = self._safe_uuid(it.collection_id)
            student_uid = self._safe_uuid(it.student_id)
            classroom_uid = self._safe_uuid(it.classroom_id)

            cert = certs_map.get(cert_uid) if cert_uid else None
            collection = colls_map.get(coll_uid) if coll_uid else None
            student = students_map.get(student_uid) if student_uid else None
            classroom = classrooms_map.get(classroom_uid) if classroom_uid else None

            issued_at_raw = getattr(it, 'issued_at', None)
            issued_at_iso = self._to_iso(issued_at_raw)

            enriched.append({
                'uid': str(it.uid),
                'student_id': str(it.student_id),
                'certificate_id': str(it.certificate_id),
                'collection_id': str(it.collection_id),
                'classroom_id': str(it.classroom_id),
                'issued_by': str(it.issued_by) if getattr(it, 'issued_by', None) else None,
                'issued_at': issued_at_iso,
                'issued_at_display': self._format_display_date(issued_at_raw),
                'pdf_url': getattr(it, 'pdf_url', None),
                'verification_code': it.verification_code,

                # Resolved human-friendly fields
                'title': cert.name if cert else (collection.title if collection else 'Certificate'),
                'description': cert.description if cert else '',
                'template_url': getattr(cert, 'template_url', None) if cert else None,

                'collection_title': collection.title if collection else '',
                'collection_description': getattr(collection, 'description', '') if collection else '',

                'student_name': self._student_display_name(student),
                'student_pid': getattr(student, 'pid', '') if student else '',
                'student_avatar_url': getattr(student, 'avatar_url', '') if student else '',

                'classroom_name': getattr(classroom, 'name', '') if classroom else '',
            })
        return enriched

    # --- internal lookups ---

    def _safe_fetch_certificates(self, cert_ids):
        out = {}
        if not cert_ids:
            return out
        try:
            for cid in cert_ids:
                try:
                    c = self.certificate_repo.find(cid)
                    out[cid] = c
                except Exception:
                    continue
        except Exception as exc:
            logger.warning(f"[Certificate] Failed to fetch certificate templates: {exc}")
        return out

    def _safe_fetch_collections(self, coll_ids):
        out = {}
        if not coll_ids:
            return out
        try:
            for cid in coll_ids:
                try:
                    c = self.collection_repo.find(cid)
                    out[cid] = c
                except Exception:
                    continue
        except Exception as exc:
            logger.warning(f"[Certificate] Failed to fetch collections: {exc}")
        return out

    def _safe_fetch_consumers(self, student_ids):
        out = {}
        if not student_ids:
            return out
        try:
            from features.account.consumer.repositories.consumer_repository import (
                ConsumerRepository,
            )
            repo = ConsumerRepository()
            for sid in student_ids:
                try:
                    c = repo.model.objects.filter(uid=sid, is_deleted=False).first()
                    if c:
                        out[sid] = c
                except Exception:
                    continue
        except Exception as exc:
            logger.warning(f"[Certificate] Failed to fetch consumers: {exc}")
        return out

    def _safe_fetch_classrooms(self, classroom_ids):
        out = {}
        if not classroom_ids:
            return out
        try:
            from features.course.classroom.models.classroom import Classroom
            for cid in classroom_ids:
                try:
                    cl = Classroom.objects.filter(uid=cid, is_deleted=False).first()
                    if cl:
                        out[cid] = cl
                except Exception:
                    continue
        except Exception as exc:
            logger.warning(f"[Certificate] Failed to fetch classrooms: {exc}")
        return out

    @staticmethod
    def _safe_uuid(val):
        if not val:
            return None
        try:
            return UUID(str(val))
        except Exception:
            return None

    @staticmethod
    def _to_iso(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat() + 'Z' if value.tzinfo is None else value.isoformat()
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _format_display_date(value):
        if not value:
            return ''
        if isinstance(value, datetime):
            try:
                return value.strftime('%d/%m/%Y')
            except Exception:
                return str(value)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', ''))
                return dt.strftime('%d/%m/%Y')
            except Exception:
                return value
        return str(value)

    @staticmethod
    def _student_display_name(student):
        if not student:
            return ''
        full = (getattr(student, 'full_name', '') or '').strip()
        if full:
            return full
        first = (getattr(student, 'first_name', '') or '').strip()
        last = (getattr(student, 'last_name', '') or '').strip()
        if first or last:
            return f"{first} {last}".strip()
        username = (getattr(student, 'username', '') or '').strip()
        if username:
            return username
        pid = (getattr(student, 'pid', '') or '').strip()
        return pid
