from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class SocialPost(BaseTimeStampModel):
    """
    Posts created by any owner (consumer or space).
    Partition by owner_id → get all posts by a user.
    Global feed scans all partitions and filters in Python.
    """

    owner_id     = columns.UUID(partition_key=True, primary_key=True, required=True)
    owner_type   = columns.Text(partition_key=True, primary_key=True, required=True, default='consumer')
    created_at   = columns.DateTime(primary_key=True, clustering_order='DESC', default=datetime.utcnow)
    uid          = columns.UUID(primary_key=True, default=uuid7)

    owner_name    = columns.Text(default='')
    owner_avatar  = columns.Text(default='')

    space_uid      = columns.UUID(index=True, required=False)

    content        = columns.Text(default='')
    emotion        = columns.Text(default='')
    image_url      = columns.Text(default='')
    image_urls     = columns.List(columns.Text, default=list)
    visibility     = columns.Text(default='public')
    classroom_tags = columns.List(columns.UUID, required=False)

    likes_count    = columns.Integer(default=0)
    comments_count = columns.Integer(default=0)

    __table_name__ = 'social_posts'

    class Meta:
        get_pk_field = 'uid'
