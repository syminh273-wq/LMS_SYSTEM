from core.repositories.base_repository import BaseRepository
from features.course.models import CourseEnrollmentByConsumer


class CourseEnrollmentByConsumerRepository(BaseRepository):
    """Lookup enrollment by consumer (student-side queries)."""

    model = CourseEnrollmentByConsumer

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

    def upsert(self, consumer_id, course_uid, **fields):
        existing = self.get_for_consumer(consumer_id, course_uid)
        if existing:
            return self.update(existing, is_deleted=False, **fields)
        return self.create(
            consumer_id=consumer_id,
            course_uid=course_uid,
            **fields,
        )

    def soft_delete(self, consumer_id, course_uid):
        existing = self.get_for_consumer(consumer_id, course_uid)
        if existing and not existing.is_deleted:
            self.update(existing, is_deleted=True)
        return existing
