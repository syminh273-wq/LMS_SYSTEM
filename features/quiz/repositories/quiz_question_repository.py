from core.repositories.base_repository import BaseRepository
from features.quiz.models.quiz_question import QuizQuestion


class QuizQuestionRepository(BaseRepository):
    model = QuizQuestion

    def get_by_quiz(self, quiz_id):
        return self.filter(quiz_id=quiz_id, is_deleted=False)

    def bulk_create(self, questions: list):
        created = []
        for q in questions:
            created.append(self.create(**q))
        return created
