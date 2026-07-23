import uuid
from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class Portfolio(BaseTimeStampModel):
    __table_name__ = 'portfolios'

    uid = columns.UUID(primary_key=True, default=uuid.uuid4)
    owner_id = columns.UUID(index=True)
    owner_type = columns.Text(index=True)
    key = columns.Text()
    value = columns.Text(default='{}')
    is_public = columns.Boolean(default=True)
    display_order = columns.Integer(default=0)
    is_deleted = columns.Boolean(default=False)
    deleted_at = columns.DateTime(required=False)

    VALID_KEYS = ('intro', 'certificate', 'experience', 'achievement', 'course', 'education')
    OWNER_TYPES = ('space', 'consumer')
