from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Certificate(BaseTimeStampModel):
    """
    Teacher-owned certificate template. Reusable across many collections.
    """
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    created_by = columns.UUID(index=True, required=True)
    name = columns.Text(required=True)
    description = columns.Text(default='')
    template_url = columns.Text(required=False)
    is_active = columns.Boolean(default=True)

    __table_name__ = 'certificates'

    class Meta:
        get_pk_field = 'uid'
