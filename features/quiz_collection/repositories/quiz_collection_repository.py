from core.repositories.base_repository import BaseRepository
from features.quiz_collection.models import QuizCollection


class QuizCollectionRepository(BaseRepository):
    model = QuizCollection

    def get_by_teacher(self, teacher_id):
        return self.filter(created_by=teacher_id, is_deleted=False)

    def get_by_uids(self, uids: list):
        results = []
        for uid in uids:
            try:
                results.append(self.find(uid))
            except self.model.DoesNotExist:
                pass
        return results
