from datetime import datetime

from features.quiz.models.quiz_play import QuizPlay
from core.utils.uuid import uuid7


class QuizPlayRepository:

    def get_by_classroom(self, quiz_id, classroom_id):
        return QuizPlay.objects.filter(quiz_id=quiz_id, classroom_id=classroom_id)

    def get_by_student(self, quiz_id, classroom_id, student_id):
        return QuizPlay.objects.filter(
            quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
        )

    def count_by_student(self, quiz_id, classroom_id, student_id) -> int:
        return len(list(
            QuizPlay.objects.filter(
                quiz_id=quiz_id, classroom_id=classroom_id, student_id=student_id
            )
        ))

    def create_play(self, quiz_id, classroom_id, student_id, attempt_number,
                    score, total_questions, score_pct, time_taken_seconds,
                    answers: dict) -> QuizPlay:
        return QuizPlay.objects.create(
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
