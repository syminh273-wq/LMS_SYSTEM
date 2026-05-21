from core.repositories.base_repository import BaseRepository
from features.quiz.models.quiz import Quiz


class QuizRepository(BaseRepository):
    model = Quiz

    def get_by_teacher(self, teacher_id):
        return self.filter(created_by=teacher_id, is_deleted=False)

    def get_by_uids(self, uids: list):
        results = []
        for uid in uids:
            try:
                quiz = self.find(uid)
                results.append(quiz)
            except self.model.DoesNotExist:
                pass
        return results
