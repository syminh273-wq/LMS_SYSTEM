import logging
from datetime import datetime
from features.course.repositories import (
    CourseEnrollmentByConsumerRepository,
    CourseEnrollmentByCourseRepository,
)

logger = logging.getLogger(__name__)


class CourseEnrollmentService:
    """
    Lightweight enrollment ledger.

    The previous `course_courses` table was removed; enrollments are now
    purely historical records keyed by (consumer, course_uid) and
    (course_uid, consumer).  The actual classroom join still lives in
    `course_classroom_members`.
    """

    def __init__(self):
        self.by_consumer_repo = CourseEnrollmentByConsumerRepository()
        self.by_course_repo = CourseEnrollmentByCourseRepository()

    def is_enrolled(self, consumer_id, course_uid) -> bool:
        return self.by_consumer_repo.is_enrolled(consumer_id, course_uid)

    def list_for_consumer(self, consumer_id):
        return list(self.by_consumer_repo.list_for_consumer(consumer_id))

    def list_for_course(self, course_uid):
        rows = list(self.by_course_repo.list_for_course(course_uid))
        return [{
            'consumer_id': r.consumer_id,
            'consumer_name': r.consumer_name_snapshot,
            'consumer_avatar': r.consumer_avatar_snapshot,
            'enrolled_at': r.enrolled_at,
            'pricing_type': r.pricing_type,
            'amount_vnd': int(r.amount_vnd or 0),
            'payment_order_id': r.payment_order_id,
        } for r in rows]

    def get_access(self, consumer_id, course_uid):
        return {'enrolled': self.is_enrolled(consumer_id, course_uid)}

    def record_enrollment(
        self,
        consumer_id,
        course_uid,
        consumer_name='',
        consumer_avatar='',
        pricing_type='free',
        amount_vnd=0,
        payment_order_id=None,
    ):
        common_fields = {
            'status': 'enrolled',
            'enrolled_at': datetime.utcnow(),
            'pricing_type': pricing_type,
            'amount_vnd': amount_vnd,
            'payment_order_id': payment_order_id,
        }
        self.by_consumer_repo.upsert(consumer_id, course_uid, **common_fields)
        return self.by_course_repo.upsert(
            course_uid,
            consumer_id,
            consumer_name_snapshot=consumer_name,
            consumer_avatar_snapshot=consumer_avatar,
            **common_fields,
        )
