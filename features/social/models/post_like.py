from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class PostLike(DjangoCassandraModel):
    """
    Like/unlike a post. One row per (post, user) pair.
    Partition by post_uid for fast like-count queries.
    """

    post_uid     = columns.UUID(partition_key=True, required=True)
    consumer_uid = columns.UUID(primary_key=True, clustering_order='ASC', required=True)
    created_at   = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'post_likes'

    class Meta:
        get_pk_field = 'consumer_uid'
