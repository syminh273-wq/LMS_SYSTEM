from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class PostLike(BaseTimeStampModel):
    """
    Like/unlike a post. One row per (post, user) pair.
    Partition by post_uid for fast like-count queries.
    """

    post_uid     = columns.UUID(partition_key=True, required=True)
    consumer_uid = columns.UUID(primary_key=True, clustering_order='ASC', required=True)

    __table_name__ = 'post_likes'

    class Meta:
        get_pk_field = 'consumer_uid'
