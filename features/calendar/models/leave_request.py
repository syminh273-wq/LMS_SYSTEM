from core.utils.uuid import uuid7
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel

class LeaveRequest(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    student_id = columns.UUID(index=True, required=True)
    space_id = columns.UUID(index=True, required=True)

    classroom_id = columns.UUID(index=True, required=False)

    # Can be for a specific event or a date range
    event_id = columns.UUID(index=True, required=False)
    start_date = columns.DateTime(required=False)
    end_date = columns.DateTime(required=False)

    reason = columns.Text(required=True)
    evidence_url = columns.Text(required=False) # Link to R2 storage

    # Status: pending, approved, rejected
    status = columns.Text(default='pending', index=True)

    processed_by = columns.UUID(required=False) # Teacher ID
    processed_at = columns.DateTime(required=False)
    rejection_reason = columns.Text(required=False)

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'calendar_leave_requests'
