from datetime import datetime

from features.quiz.models.quiz_attempt import QuizAttempt
from core.utils.uuid import uuid7


class QuizAttemptRepository:

    def get_by_classroom(self, quiz_id, classroom_id):
        return QuizAttempt.objects.filter(quiz_id=quiz_id, classroom_id=classroom_id)

    def get_by_student(self, quiz_id, classroom_id, student_id):
        return QuizAttempt.objects.filter(
            quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
        )

    def count_by_student(self, quiz_id, classroom_id, student_id) -> int:
        return len(list(
            QuizAttempt.objects.filter(
                quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
            )
        ))

    def create_attempt(self, quiz_id, classroom_id, student_id, attempt_number,
                       score, total_questions, score_pct, time_taken_seconds,
                       answers: dict) -> QuizAttempt:
        return QuizAttempt.objects.create(
            quiz_id=quiz_id,
            classroom_id=classroom_id,
            student_id=student_id,
            uid=uuid7(),
            attempt_number=attempt_number,
            score=score,
            total_questions=total_questions,
            score_pct=score_pct,
            time_taken_seconds=time_taken_seconds,
            answers=answers,
            submitted_at=datetime.now(),
        )
