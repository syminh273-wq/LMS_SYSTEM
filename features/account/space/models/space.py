from uuid import uuid4
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class Space(BaseTimeStampModel):
    __table_name__ = 'account_spaces'

    uid = columns.UUID(primary_key=True, default=uuid4)
    owner_uid = columns.UUID(index=True, required=False)
    name = columns.Text(default='')
    slug = columns.Text(index=True, default='')
    description = columns.Text(default='')
    logo_url = columns.Text(default='')
    cover_url = columns.Text(default='')
    is_active = columns.Boolean(default=True)

    # is_deleted, deleted_at, created_at, updated_at → BaseTimeStampModel
