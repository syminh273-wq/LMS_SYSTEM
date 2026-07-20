from core.repositories.base_repository import BaseRepository
from features.course.models import CourseLesson


class CourseLessonRepository(BaseRepository):
    model = CourseLesson

    def get_by_course(self, course_uid):
        return self.filter(
            bucket=0, course_uid=course_uid, is_deleted=False
        ).order_by('order_index', 'uid')

    def get_preview_lessons(self, course_uid):
        return self.filter(
            bucket=0,
            course_uid=course_uid,
            is_preview=True,
            is_published=True,
            is_deleted=False,
        ).order_by('order_index', 'uid')

    def get_published_lessons(self, course_uid):
        return self.filter(
            bucket=0,
            course_uid=course_uid,
            is_published=True,
            is_deleted=False,
        ).order_by('order_index', 'uid')

    def next_order_index(self, course_uid) -> int:
        existing = self.get_by_course(course_uid)
        if not existing:
            return 0
        max_idx = -1
        for l in existing:
            if l.order_index > max_idx:
                max_idx = l.order_index
        return max_idx + 1
