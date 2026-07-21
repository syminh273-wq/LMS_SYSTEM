from datetime import datetime

from core.utils.uuid import uuid7
from features.quiz.models.quiz_log import QuizLog


class QuizLogRepository:

    def get_by_classroom(self, quiz_id, classroom_id):
        return QuizLog.objects.filter(quiz_id=quiz_id, classroom_id=classroom_id)

    def get_by_student(self, quiz_id, classroom_id, student_id):
        return QuizLog.objects.filter(
            quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
        )

    def count_by_student(self, quiz_id, classroom_id, student_id) -> int:
        return len(list(
            QuizLog.objects.filter(
                quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
            )
        ))

    def iter_classroom_logs(self, classroom_id):
        """Iterate every quiz log in a classroom across all quizzes (ALLOW FILTERING)."""
        return QuizLog.objects.filter(classroom_id=classroom_id).allow_filtering()

    def create(self, quiz_id, classroom_id, student_id, attempt_number,
               score, total_questions, score_pct, time_taken_seconds,
               answers: dict, source: str = "game", exam_id=None) -> QuizLog:
        return QuizLog.objects.create(
            uid=uuid7(),
            quiz_id=quiz_id,
            classroom_id=classroom_id,
            student_id=student_id,
            source=source,
            exam_id=exam_id,
            answers={str(k): str(v) for k, v in answers.items()},
            time_taken_seconds=time_taken_seconds,
            submitted_at=datetime.now(),
            attempt_number=attempt_number,
            score=score,
            total_questions=total_questions,
            score_pct=score_pct,
            graded_at=datetime.now(),
        )
