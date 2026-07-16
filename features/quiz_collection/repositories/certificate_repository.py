from core.repositories.base_repository import BaseRepository
from features.quiz_collection.models import Certificate


class CertificateRepository(BaseRepository):
    model = Certificate

    def get_by_teacher(self, teacher_id):
        return self.filter(created_by=teacher_id, is_deleted=False)

    def get_active_by_teacher(self, teacher_id):
        return self.filter(created_by=teacher_id, is_deleted=False, is_active=True)
