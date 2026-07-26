from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class CourseEnrollmentByConsumer(BaseTimeStampModel):
    """
    Enrollment lookup keyed by consumer.
    Partition = consumer_id  →  fast "all courses a student enrolled in".
    One row per (consumer, course) pair — write-through with CourseEnrollmentByCourse.
    """

    consumer_id   = columns.UUID(partition_key=True, primary_key=True, required=True)
    course_uid    = columns.UUID(primary_key=True, clustering_order="DESC", required=True)

    status            = columns.Text(default='enrolled')
    enrolled_at       = columns.DateTime(default=datetime.utcnow, required=True)
    payment_order_id  = columns.Text(required=False)
    pricing_type      = columns.Text(default='free')
    amount_vnd        = columns.BigInt(default=0)

    class Meta:
        get_pk_field = 'course_uid'

    __table_name__ = 'course_enrollments_by_consumer'
