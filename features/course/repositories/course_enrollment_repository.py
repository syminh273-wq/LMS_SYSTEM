from core.repositories.base_repository import BaseRepository
from features.course.models import CourseEnrollment


class CourseEnrollmentRepository(BaseRepository):
    model = CourseEnrollment

    def is_enrolled(self, consumer_id, course_uid) -> bool:
        row = self.filter(
            consumer_id=consumer_id,
            course_uid=course_uid,
            is_deleted=False,
            status='enrolled',
        ).first()
        return row is not None

    def get_for_consumer(self, consumer_id, course_uid):
        return self.filter(
            consumer_id=consumer_id, course_uid=course_uid
        ).first()

    def list_for_consumer(self, consumer_id):
        return self.filter(
            consumer_id=consumer_id, is_deleted=False, status='enrolled'
        )

    def list_for_course(self, course_uid):
        return self.filter(
            course_uid=course_uid, is_deleted=False, status='enrolled'
        )

    def count_for_course(self, course_uid) -> int:
        return self.list_for_course(course_uid).count()
