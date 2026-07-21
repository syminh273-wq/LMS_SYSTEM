from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ResourceFolder(BaseTimeStampModel):
    classroom_id = columns.UUID(partition_key=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    name = columns.Text(required=True)
    parent_folder_id = columns.UUID(required=False)
    owner_id = columns.UUID(index=True)
    order_index = columns.Integer(default=0)
    color = columns.Text(required=False)
    is_preview_only = columns.Boolean(default=False, index=True)

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'resource_folders'
