from core.services.base_service import BaseService
from core.utils.uuid import uuid7
from features.quiz.repositories.quiz_repository import QuizRepository
from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository
from features.quiz.repositories.quiz_assignment_repository import QuizAssignmentRepository
from features.quiz.repositories.quiz_attempt_repository import QuizAttemptRepository


class QuizService(BaseService):
    def __init__(self):
        self.repository = QuizRepository()
        self.question_repo = QuizQuestionRepository()
        self.assignment_repo = QuizAssignmentRepository()
        self.attempt_repo = QuizAttemptRepository()

    # ── Quiz queries ─────────────────────────────────────────────────────────

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def get_by_classroom(self, classroom_id):
        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        quiz_ids = [a.quiz_id for a in assignments]
        return self.repository.get_by_uids(quiz_ids)

    def get_with_questions(self, quiz_uid):
        quiz = self.repository.find(quiz_uid)
        questions = list(self.question_repo.get_by_quiz(quiz_uid))
        return quiz, questions

    # ── Assignment ───────────────────────────────────────────────────────────

    def get_assigned_classrooms(self, quiz_uid):
        return self.assignment_repo.get_by_quiz(quiz_uid)

    def get_assignment(self, quiz_uid, classroom_id):
        return self.assignment_repo.find_assignment(quiz_uid, classroom_id)

    def assign_to_classroom(self, quiz_uid, classroom_id, assigned_by, **kwargs):
        self.repository.find(quiz_uid)   # ensure quiz exists
        return self.assignment_repo.assign(
            quiz_uid, classroom_id, assigned_by, **kwargs
        )

    def update_assignment_settings(self, quiz_uid, classroom_id, **kwargs):
        return self.assignment_repo.update_settings(quiz_uid, classroom_id, **kwargs)

    def unassign_from_classroom(self, quiz_uid, classroom_id):
        self.assignment_repo.unassign(quiz_uid, classroom_id)

    # ── Quiz creation ─────────────────────────────────────────────────────────

    def create_quiz_with_questions(self, created_by, title, description, resource_id, questions: list):
        quiz_uid = uuid7()
        quiz = self.repository.create(
            uid=quiz_uid,
            created_by=created_by,
            resource_id=resource_id,
            title=title,
            description=description,
            questions_count=len(questions),
            status='published',
        )
        question_payloads = [
            {
                'quiz_id': quiz_uid,
                'uid': uuid7(),
                'question_text': q['question'],
                'option_a': q['options']['a'],
                'option_b': q['options']['b'],
                'option_c': q['options']['c'],
                'option_d': q['options']['d'],
                'correct_answer': q['correct'],
                'explanation': q.get('explanation', ''),
                'order': idx,
            }
            for idx, q in enumerate(questions)
        ]
        created_questions = self.question_repo.bulk_create(question_payloads)
        return quiz, created_questions

    def create_quiz_shell(self, created_by, title, description, resource_id=None):
        return self.repository.create(
            uid=uuid7(),
            created_by=created_by,
            resource_id=resource_id,
            title=title,
            description=description,
            questions_count=0,
            status='draft',
        )

    def add_question(self, quiz, question_data: dict, index: int):
        return self.question_repo.create(
            quiz_id=quiz.uid,
            uid=uuid7(),
            question_text=question_data['question'],
            option_a=question_data['options']['a'],
            option_b=question_data['options']['b'],
            option_c=question_data['options']['c'],
            option_d=question_data['options']['d'],
            correct_answer=question_data['correct'],
            explanation=question_data.get('explanation', ''),
            order=index,
        )

    def finalize_quiz(self, quiz, total_questions: int):
        return self.repository.update(quiz, questions_count=total_questions, status='published')

    # ── Attempts (all scoped by classroom) ────────────────────────────────────

    def get_student_attempt_count(self, quiz_uid, classroom_id, student_uid) -> int:
        return self.attempt_repo.count_by_student(quiz_uid, classroom_id, student_uid)

    def record_attempt(self, quiz_uid, classroom_id, student_uid, attempt_number,
                       score, total_questions, score_pct, time_taken_seconds, answers: dict):
        return self.attempt_repo.create_attempt(
            quiz_id=quiz_uid,
            classroom_id=classroom_id,
            student_id=student_uid,
            attempt_number=attempt_number,
            score=score,
            total_questions=total_questions,
            score_pct=score_pct,
            time_taken_seconds=time_taken_seconds,
            answers=answers,
        )

    def get_all_attempts(self, quiz_uid, classroom_id):
        return self.attempt_repo.get_by_classroom(quiz_uid, classroom_id)

    def get_student_attempts(self, quiz_uid, classroom_id, student_uid):
        return self.attempt_repo.get_by_student(quiz_uid, classroom_id, student_uid)

    # ── Question update ───────────────────────────────────────────────────────

    def find_question(self, quiz_id, question_uid):
        return self.question_repo.find_question(quiz_id, question_uid)

    def update_question(self, question, **fields):
        return self.question_repo.update(question, **fields)

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_quiz(self, quiz_uid):
        quiz = self.repository.find(quiz_uid)
        for assignment in self.assignment_repo.get_by_quiz(quiz_uid):
            assignment.delete()
        for q in self.question_repo.get_by_quiz(quiz_uid):
            self.question_repo.delete(q)
        self.repository.delete(quiz)
