from features.quiz.repositories.quiz_log_repository import QuizLogRepository
from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository


class QuizLogService:
    def __init__(self):
        self.log_repo      = QuizLogRepository()
        self.question_repo = QuizQuestionRepository()

    def _grade(self, quiz_id, answers: dict, max_grade: float):
        questions = list(self.question_repo.get_by_quiz(quiz_id))
        total = len(questions)
        if not total:
            return 0, 0, 0, 0.0

        correct_count = sum(
            1 for q in questions
            if str(q.uid) in answers and answers[str(q.uid)] == q.correct_answer
        )
        score_pct = round((correct_count / total) * 100)
        score     = round((correct_count / total) * float(max_grade), 2)
        return correct_count, total, score_pct, score

    def create(self, quiz_id, classroom_id, student_id, answers: dict,
               time_taken_seconds: int = 0, max_grade: float = 10.0,
               attempt_number: int = 1, source: str = "game", exam_id=None):
        correct_count, total, score_pct, score = self._grade(quiz_id, answers, max_grade)
        log = self.log_repo.create(
            quiz_id=quiz_id,
            classroom_id=classroom_id,
            student_id=student_id,
            attempt_number=attempt_number,
            score=correct_count,
            total_questions=total,
            score_pct=score_pct,
            time_taken_seconds=time_taken_seconds,
            answers=answers,
            source=source,
            exam_id=exam_id,
        )

        # Award XP for this quiz attempt. Idempotent per (student, quiz_log_uid).
        try:
            from features.ranking.services.xp_service import XPService
            xp = XPService()
            xp.award(
                student_id=student_id,
                event_type='quiz_submitted',
                ref_type='quiz_log',
                ref_id=log.uid,
                classroom_id=classroom_id,
                description=f'Nộp bài quiz: {score_pct}%',
                metadata={'quiz_id': str(quiz_id), 'score_pct': score_pct},
            )
            passing = 50
            try:
                from features.quiz.repositories.quiz_assignment_repository import QuizAssignmentRepository
                assign = QuizAssignmentRepository().find_assignment(quiz_id, classroom_id)
                if assign and assign.passing_score_pct:
                    passing = int(assign.passing_score_pct)
            except Exception:
                pass
            if score_pct >= passing:
                xp.award(
                    student_id=student_id,
                    event_type='quiz_passed',
                    ref_type='quiz_log',
                    ref_id=log.uid,
                    classroom_id=classroom_id,
                    description=f'Đậu bài quiz: {score_pct}%',
                    metadata={'quiz_id': str(quiz_id), 'score_pct': score_pct},
                    count_field='quizzes_passed_count',
                )
            if score_pct >= 100:
                xp.award(
                    student_id=student_id,
                    event_type='quiz_perfect',
                    ref_type='quiz_log',
                    ref_id=log.uid,
                    classroom_id=classroom_id,
                    description=f'Đạt 100% bài quiz',
                    metadata={'quiz_id': str(quiz_id)},
                    count_field='perfect_scores_count',
                )
        except Exception:
            pass

        return log, correct_count, total, score_pct, score

    def count_attempts(self, quiz_id, classroom_id, student_id) -> int:
        return self.log_repo.count_by_student(quiz_id, classroom_id, student_id)

    def list_by_student(self, quiz_id, classroom_id, student_id):
        return self.log_repo.get_by_student(quiz_id, classroom_id, student_id)

    def list_by_classroom(self, quiz_id, classroom_id):
        return self.log_repo.get_by_classroom(quiz_id, classroom_id)
