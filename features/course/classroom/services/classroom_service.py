import string
import random
from features.course.classroom.repositories import Repository
from features.sharing.services import LinkService
from features.sharing.enums import ResourceType

class Service:
    def __init__(self):
        self.repository = Repository()
        self.link_service = LinkService()

    def all(self):
        return self.repository.all()

    def find(self, uid):
        return self.repository.find(uid)

    def get_active_classrooms(self):
        return self.repository.get_active_classrooms()

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def create_classroom(self, teacher_id, data: dict):
        # Generate a unique 6-char uppercase alphanumeric pid (invite code)
        pid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        classroom = self.repository.create(teacher_id=teacher_id, pid=pid, **data)

        # Create a short link for this classroom
        self.link_service.create_link({
            'code': pid,
            'resource_type': ResourceType.CLASSROOM.value,
            'resource_id': classroom.uid,
            'action': 'join',
            'metadata': {
                'name': classroom.name
            }
        })

        return classroom

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance):
        # Soft delete using the repository's delete method (which typically handles is_deleted)
        return self.repository.delete(instance)
