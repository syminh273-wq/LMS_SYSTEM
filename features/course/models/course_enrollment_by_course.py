from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class CourseEnrollmentByCourse(BaseTimeStampModel):
    """
    Enrollment lookup keyed by course.
    Partition = course_uid  →  fast "all students in course X" (teacher view).
    One row per (course, consumer) pair — write-through with CourseEnrollmentByConsumer.
    """

    course_uid    = columns.UUID(partition_key=True, primary_key=True, required=True)
    consumer_id   = columns.UUID(primary_key=True, clustering_order="DESC", required=True)

    status            = columns.Text(default='enrolled')
    enrolled_at       = columns.DateTime(default=datetime.utcnow, required=True)
    payment_order_id  = columns.Text(required=False)
    pricing_type      = columns.Text(default='free')
    amount_vnd        = columns.BigInt(default=0)

    consumer_name_snapshot   = columns.Text(default='')
    consumer_avatar_snapshot = columns.Text(default='')

    class Meta:
        get_pk_field = 'consumer_id'

    __table_name__ = 'course_enrollments_by_course'
