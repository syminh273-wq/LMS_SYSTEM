from core.repositories.base_repository import BaseRepository
from features.course.models import CourseEnrollmentByCourse


class CourseEnrollmentByCourseRepository(BaseRepository):
    """Lookup enrollment by course (teacher-side queries)."""

    model = CourseEnrollmentByCourse

    def get_for_course(self, course_uid, consumer_id):
        return self.filter(
            course_uid=course_uid, consumer_id=consumer_id
        ).first()

    def list_for_course(self, course_uid):
        return self.filter(
            course_uid=course_uid, is_deleted=False, status='enrolled'
        )

    def count_for_course(self, course_uid) -> int:
        return self.list_for_course(course_uid).count()

    def upsert(self, course_uid, consumer_id, **fields):
        existing = self.get_for_course(course_uid, consumer_id)
        if existing:
            return self.update(existing, is_deleted=False, **fields)
        return self.create(
            course_uid=course_uid,
            consumer_id=consumer_id,
            **fields,
        )

    def soft_delete(self, course_uid, consumer_id):
        existing = self.get_for_course(course_uid, consumer_id)
        if existing and not existing.is_deleted:
            self.update(existing, is_deleted=True)
        return existing
