import logging
import secrets
import string

from features.quiz_collection.repositories import (
    QuizCollectionRepository,
    QuizCollectionItemRepository,
    QuizCollectionAssignmentRepository,
    CertificateRepository,
    IssuedCertificateRepository,
)

logger = logging.getLogger(__name__)

_VERIFICATION_ALPHABET = string.ascii_uppercase + string.digits


def _generate_verification_code(length: int = 12) -> str:
    return ''.join(secrets.choice(_VERIFICATION_ALPHABET) for _ in range(length))


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

    def check_and_issue(self, student_id, classroom_id, just_submitted_quiz_id):
        from features.quiz_collection.services.notification_service_helper import notify_issued

        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        if not assignments:
            return []

        issued_now = []
        for assignment in assignments:
            collection_id = str(assignment.collection_id)
            try:
                collection = self.collection_repo.find(collection_id)
            except Exception:
                continue

            if str(just_submitted_quiz_id) not in self.item_repo.get_quiz_ids(collection_id):
                continue

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

            issued = self.issued_repo.create(
                student_id=student_id,
                certificate_id=certificate_id,
                collection_id=collection_id,
                classroom_id=classroom_id,
                issued_by=str(collection.created_by),
                verification_code=_generate_verification_code(),
            )
            issued_now.append(issued)

            try:
                notify_issued(student_id, collection, issued)
            except Exception as exc:
                logger.warning(f"[Certificate] Notification failed: {exc}")

        return issued_now

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
            passing = assignment.passing_score_pct or 50

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

        from features.quiz.repositories.quiz_log_repository import QuizLogRepository

        log_repo = QuizLogRepository()
        assignment_repo = QuizAssignmentRepository()

        passed_quiz_ids = []
        for quiz_id in quiz_ids:
            assignment = assignment_repo.find_assignment(quiz_id, classroom_id)
            if not assignment:
                continue
            passing = assignment.passing_score_pct or 50
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
        return {
            'total': total,
            'passed': passed,
            'is_completed': passed == total,
            'percent': percent,
            'passed_quiz_ids': passed_quiz_ids,
            'missing_quiz_ids': [q for q in quiz_ids if q not in passed_quiz_ids],
        }
