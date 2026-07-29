from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Dummy(BaseTimeStampModel):
    """Scaffolded Cassandra model. Edit columns to match the feature.

    Partition key: `uid` (UUID v7, time-sortable).
    Soft delete: handled by `BaseTimeStampModel` via `is_deleted` / `deleted_at`.
    """

    uid = columns.UUID(primary_key=True, default=uuid7)
    owner_id = columns.UUID(index=True, required=True)
    name = columns.Text(required=True)
    description = columns.Text(default='')
    status = columns.Text(default='active', index=True)

    __table_name__ = 'dummies'

    class Meta:
        get_pk_field = 'uid'
