from core.utils.uuid import uuid7
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel

class CalendarEvent(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    
    # Types: class, exam, deadline, study_session
    type = columns.Text(index=True, required=True)
    title = columns.Text(required=True)
    description = columns.Text(default='')
    
    start_time = columns.DateTime(required=True)
    end_time = columns.DateTime(required=True)
    
    # Related entity (Classroom UID, Exam UID, etc.)
    classroom_id = columns.UUID(index=True, required=False)
    space_id = columns.UUID(index=True, required=True)
    owner_id = columns.UUID(index=True, required=True) # Teacher who created it
    
    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'calendar_events'
