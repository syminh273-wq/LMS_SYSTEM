from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class SocialPostComment(BaseTimeStampModel):
    """
    Comments on a social post.
    Partition by post_uid → all comments for a post in one query.
    """

    post_uid      = columns.UUID(partition_key=True, required=True)
    created_at    = columns.DateTime(primary_key=True, clustering_order='ASC', default=datetime.utcnow)
    uid           = columns.UUID(primary_key=True, default=uuid7, clustering_order='ASC')

    owner_id      = columns.UUID(required=True)
    owner_type    = columns.Text(default='consumer')
    owner_name    = columns.Text(default='')
    owner_avatar  = columns.Text(default='')
    content       = columns.Text(default='')

    __table_name__ = 'social_post_comments'

    class Meta:
        get_pk_field = 'uid'
