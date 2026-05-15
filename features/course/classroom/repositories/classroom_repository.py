from core.repositories.base_repository import BaseRepository
from features.course.classroom.models import Classroom

class Repository(BaseRepository):
    model = Classroom

    def get_active_classrooms(self):
        # We must filter by bucket to use ORDER BY uid in Cassandra
        return self.filter(bucket=0, status='active', is_deleted=False).order_by('uid')

    def get_by_teacher(self, teacher_id):
        # Global filter without order_by will work fine
        return self.filter(teacher_id=teacher_id, is_deleted=False)
