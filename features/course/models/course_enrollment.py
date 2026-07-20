from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class CourseEnrollment(BaseTimeStampModel):
    consumer_id = columns.UUID(partition_key=True)
    course_uid = columns.UUID(primary_key=True, clustering_order="DESC", index=True)
    status = columns.Text(default='enrolled')
    enrolled_at = columns.DateTime(default=datetime.utcnow)
    payment_order_id = columns.Text(required=False)
    pricing_type = columns.Text(default='free')
    amount_vnd = columns.BigInt(default=0)

    class Meta:
        get_pk_field = 'course_uid'

    __table_name__ = 'course_enrollments'
