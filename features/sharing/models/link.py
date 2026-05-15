from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7

class Link(BaseTimeStampModel):
    uid = columns.UUID(primary_key=True, default=uuid7)

    code = columns.Text(required=True, index=True)

    resource_type = columns.Text(required=True, index=True)
    resource_id = columns.UUID(required=True, index=True)

    action = columns.Text()

    expired_at = columns.DateTime()

    max_usage = columns.Integer(default=0)
    used_count = columns.Integer(default=0)

    is_active = columns.Boolean(default=True, index=True)

    metadata = columns.Map(
        columns.Text(),
        columns.Text(),
    )

    __table_name__ = 'sharing_links'

    class Meta:
        get_pk_field = 'uid'
