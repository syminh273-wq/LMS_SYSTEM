from core.repositories.base_repository import BaseRepository
from features.quiz.models.quiz_question import QuizQuestion


class QuizQuestionRepository(BaseRepository):
    model = QuizQuestion

    def get_by_quiz(self, quiz_id):
        return self.filter(quiz_id=quiz_id, is_deleted=False)

    def find_question(self, quiz_id, uid):
        instance = self.filter(quiz_id=quiz_id, uid=uid, is_deleted=False).first()
        if not instance:
            raise self.model.DoesNotExist('QuizQuestion not found.')
        return instance

    def bulk_create(self, questions: list):
        created = []
        for q in questions:
            created.append(self.create(**q))
        return created
