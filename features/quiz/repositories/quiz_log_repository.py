import json
from datetime import datetime

from core.utils.uuid import uuid7
from features.quiz.models.quiz_log import QuizLog
from core.repositories.base_repository import BaseRepository


def encode_answer(selected: list) -> str:
    """Encode a question's selected answers as a JSON list string, e.g. '["a","c"]'."""
    return json.dumps(list(selected or []))


def decode_answer(raw: str) -> list:
    """Decode an answers map value. Tolerates legacy plain-letter values (pre multi_answer)."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return [raw]
    return parsed if isinstance(parsed, list) else [raw]


class QuizLogRepository(BaseRepository):
    model = QuizLog

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
        """`answers` is {question_uid: [selected_answer_letters]}."""
        return QuizLog.objects.create(
            uid=uuid7(),
            quiz_id=quiz_id,
            classroom_id=classroom_id,
            student_id=student_id,
            source=source,
            exam_id=exam_id,
            answers={str(k): encode_answer(v) for k, v in answers.items()},
            time_taken_seconds=time_taken_seconds,
            submitted_at=datetime.now(),
            attempt_number=attempt_number,
            score=score,
            total_questions=total_questions,
            score_pct=score_pct,
            graded_at=datetime.now(),
        )
