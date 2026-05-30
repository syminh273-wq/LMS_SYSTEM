from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

class TeacherSetting(DjangoCassandraModel):
    """
    Teacher-specific settings stored as key-value pairs.
    Partition key is teacher_uid, clustering key is key.
    """
    teacher_uid = columns.UUID(primary_key=True, partition_key=True)
    key         = columns.Text(primary_key=True)
    value       = columns.Text(default='{}')  # Stores JSON string
    
    updated_at  = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'teacher_settings'

    class Meta:
        get_pk_field = 'teacher_uid'
