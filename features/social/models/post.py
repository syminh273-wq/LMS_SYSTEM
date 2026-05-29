from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class ConsumerPost(DjangoCassandraModel):
    """
    Posts created by consumers (students).
    Partition by consumer_uid → get all posts by a user.
    Bucket 0 allows scanning all public posts for the feed.
    """

    bucket       = columns.Integer(partition_key=True, default=0)
    created_at   = columns.DateTime(primary_key=True, clustering_order='DESC', default=datetime.utcnow)
    uid          = columns.UUID(primary_key=True, default=uuid7, clustering_order='DESC')

    consumer_uid   = columns.UUID(index=True, required=True)
    author_name    = columns.Text(default='')    # snapshot
    author_avatar  = columns.Text(default='')    # snapshot

    content        = columns.Text(default='')
    emotion        = columns.Text(default='')    # happy|sad|motivated|excited|...
    image_url      = columns.Text(default='')
    visibility     = columns.Text(default='public')  # public|private|friends
    classroom_tag  = columns.UUID(required=False)

    likes_count    = columns.Integer(default=0)
    comments_count = columns.Integer(default=0)
    is_deleted     = columns.Boolean(default=False)

    __table_name__ = 'consumer_posts'

    class Meta:
        get_pk_field = 'uid'
