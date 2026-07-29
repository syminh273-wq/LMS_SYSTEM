from datetime import timedelta

from django.conf import settings

from core.services.base_service import BaseService
from core.utils.uuid import uuid7
from core.search_engine.typesense.indexer import LMSIndexer
from features.quiz.repositories.quiz_repository import QuizRepository
from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository
from features.quiz.repositories.quiz_assignment_repository import QuizAssignmentRepository
from features.quiz.repositories.quiz_log_repository import QuizLogRepository


def get_submit_grace_seconds() -> int:
    return int(getattr(settings, 'QUIZ_SUBMIT_GRACE_SECONDS', 30))


class QuizClosedError(Exception):
    pass


class QuizService(BaseService):
    def __init__(self):
        self.repository = QuizRepository()
        self.question_repo = QuizQuestionRepository()
        self.assignment_repo = QuizAssignmentRepository()
        self.log_repo = QuizLogRepository()

    # ── Quiz queries ─────────────────────────────────────────────────────────

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def get_by_classroom(self, classroom_id):
        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        quiz_ids = [a.quiz_id for a in assignments]
        return self.repository.get_by_uids(quiz_ids)

    def list_teacher_quizzes(self, teacher_id, classroom_id=None):
        """Quizzes owned by a teacher, optionally scoped to one classroom's assignments."""
        if classroom_id:
            assignments = self.assignment_repo.get_by_classroom(classroom_id)
            assignment_map = {str(a.quiz_id): a for a in assignments}
            quizzes = [
                q for q in self.repository.get_by_uids(list(assignment_map.keys()))
                if str(q.created_by) == str(teacher_id)
            ]
            return quizzes, assignment_map
        return list(self.repository.get_by_teacher(teacher_id)), {}

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

    def _is_open(self, assignment, now=None):
        from core.utils.datetime import now_vn
        if assignment is None:
            return True
        if getattr(assignment, 'is_closed', False):
            return False
        current = now or now_vn()
        opens_at = getattr(assignment, 'opens_at', None)
        if opens_at is not None and current < opens_at:
            return False
        closes_at = getattr(assignment, 'closes_at', None)
        if closes_at is not None and current > closes_at + timedelta(seconds=get_submit_grace_seconds()):
            return False
        return True

    def is_not_yet_open(self, assignment, now=None):
        from core.utils.datetime import now_vn
        if assignment is None:
            return False
        opens_at = getattr(assignment, 'opens_at', None)
        if opens_at is None:
            return False
        if getattr(assignment, 'is_closed', False):
            return False
        current = now or now_vn()
        return current < opens_at

    def is_assignment_open(self, quiz_uid, classroom_id, now=None):
        assignment = self.assignment_repo.find_assignment(quiz_uid, classroom_id)
        return self._is_open(assignment, now=now)

    def get_assignment_status(self, quiz_uid, classroom_id, now=None):
        from core.utils.datetime import now_vn
        assignment = self.assignment_repo.find_assignment(quiz_uid, classroom_id)
        current = now or now_vn()
        is_open = self._is_open(assignment, now=current)
        is_closed_flag = bool(getattr(assignment, 'is_closed', False)) if assignment else False
        closes_at = getattr(assignment, 'closes_at', None) if assignment else None
        opens_at = getattr(assignment, 'opens_at', None) if assignment else None
        closed_at = getattr(assignment, 'closed_at', None) if assignment else None
        grace = timedelta(seconds=get_submit_grace_seconds())
        is_expired = (closes_at is not None and current > closes_at + grace) and not is_closed_flag
        is_not_yet_open = (opens_at is not None and current < opens_at) and not is_closed_flag
        return {
            'is_open': is_open,
            'is_closed': is_closed_flag,
            'is_expired': is_expired,
            'is_not_yet_open': is_not_yet_open,
            'opens_at': opens_at,
            'closes_at': closes_at,
            'closed_at': closed_at,
            'server_now': current,
        }

    def close_assignment(self, quiz_uid, classroom_id, closes_at=None):
        from core.utils.datetime import now_vn
        now = now_vn()
        payload = {
            'is_closed': True,
            'closed_at': now,
        }
        if closes_at is not None:
            payload['closes_at'] = closes_at
        else:
            payload['closes_at'] = now
        return self.assignment_repo.update_close_state(quiz_uid, classroom_id, **payload)

    def reopen_assignment(self, quiz_uid, classroom_id, opens_at=None, closes_at=None):
        payload = {
            'is_closed': False,
            'closed_at': None,
        }
        if opens_at is not None:
            payload['opens_at'] = opens_at
        if closes_at is not None:
            payload['closes_at'] = closes_at
        return self.assignment_repo.update_close_state(quiz_uid, classroom_id, **payload)

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
        LMSIndexer.index_quiz(quiz)
        return quiz, created_questions

    def create_quiz_shell(self, created_by, title, description, resource_id=None):
        quiz = self.repository.create(
            uid=uuid7(),
            created_by=created_by,
            resource_id=resource_id,
            title=title,
            description=description,
            questions_count=0,
            status='draft',
        )
        LMSIndexer.index_quiz(quiz)
        return quiz

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
        updated = self.repository.update(quiz, questions_count=total_questions, status='published')
        LMSIndexer.index_quiz(updated)
        return updated

    # ── Logs (all scoped by classroom) ────────────────────────────────────────

    def get_student_attempt_count(self, quiz_uid, classroom_id, student_uid) -> int:
        return self.log_repo.count_by_student(quiz_uid, classroom_id, student_uid)

    def record_attempt(self, quiz_uid, classroom_id, student_uid, attempt_number,
                       score, total_questions, score_pct, time_taken_seconds, answers: dict):
        return self.log_repo.create(
            quiz_id=quiz_uid,
            classroom_id=classroom_id,
            student_id=student_uid,
            attempt_number=attempt_number,
            score=score,
            total_questions=total_questions,
            score_pct=score_pct,
            time_taken_seconds=time_taken_seconds,
            answers=answers,
            source="game",
            exam_id=None,
        )

    def get_all_attempts(self, quiz_uid, classroom_id):
        return self.log_repo.get_by_classroom(quiz_uid, classroom_id)

    def get_student_attempts(self, quiz_uid, classroom_id, student_uid):
        return self.log_repo.get_by_student(quiz_uid, classroom_id, student_uid)

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
        LMSIndexer.remove_quiz(str(quiz_uid))
