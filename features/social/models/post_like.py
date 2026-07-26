from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialPostLike(BaseTimeStampModel):
    """
    Like/unlike a post. One row per (post, owner) pair.
    Partition by post_uid for fast like-count queries.
    """

    post_uid    = columns.UUID(partition_key=True, required=True)
    owner_id    = columns.UUID(primary_key=True, clustering_order='ASC', required=True)
    owner_type  = columns.Text(default='consumer')

    __table_name__ = 'social_post_likes'

    class Meta:
        get_pk_field = 'owner_id'
