from core.services.base_service import BaseService
from features.quiz_collection.repositories import CertificateRepository


class CertificateService(BaseService):
    def __init__(self):
        self.repository = CertificateRepository()

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def get_active_by_teacher(self, teacher_id):
        return self.repository.get_active_by_teacher(teacher_id)

    def create(self, created_by, name, description='', template_url=None):
        return self.repository.create(
            created_by=created_by,
            name=name,
            description=description,
            template_url=template_url,
            is_active=True,
        )

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance):
        self.repository.delete(instance)
