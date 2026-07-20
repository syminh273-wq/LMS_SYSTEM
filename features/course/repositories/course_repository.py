from core.repositories.base_repository import BaseRepository
from features.course.models import Course


class CourseRepository(BaseRepository):
    model = Course

    def get_published_courses(self):
        return self.filter(bucket=0, status='published', is_deleted=False).order_by('uid')

    def get_by_teacher(self, teacher_id):
        return self.filter(teacher_id=teacher_id, is_deleted=False)

    def get_by_pid(self, pid):
        return self.filter(pid=pid, is_deleted=False).first()
