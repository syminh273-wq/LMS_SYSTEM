from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel

class Attendance(BaseTimeStampModel):
    # Primary Key: (event_uid) partition, (user_uid) clustering
    event_id = columns.UUID(partition_key=True)
    user_id = columns.UUID(primary_key=True)
    
    # Status: present, absent, late, excused
    status = columns.Text(default='absent', index=True)
    
    joined_at = columns.DateTime(required=False)
    left_at = columns.DateTime(required=False)
    
    # For daily auditing
    date = columns.Date(index=True)
    
    class Meta:
        get_pk_field = 'user_id'

    __table_name__ = 'calendar_attendances'
