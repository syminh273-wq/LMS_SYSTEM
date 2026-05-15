from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7

class Resource(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    
    name = columns.Text(required=True)
    file_type = columns.Text(required=True, index=True)  # video, jpg, pdf, etc.
    url = columns.Text(required=True)
    size = columns.BigInt()
    
    owner_id = columns.UUID(index=True)
    owner_type = columns.Text(index=True)
    
    metadata = columns.Map(
        columns.Text(),
        columns.Text(),
    )

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'resource_resources'
