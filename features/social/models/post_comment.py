from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class PostComment(DjangoCassandraModel):
    """
    Comments on a post.
    Partition by post_uid → all comments for a post in one query.
    """

    post_uid      = columns.UUID(partition_key=True, required=True)
    created_at    = columns.DateTime(primary_key=True, clustering_order='ASC', default=datetime.utcnow)
    uid           = columns.UUID(primary_key=True, default=uuid7, clustering_order='ASC')

    consumer_uid  = columns.UUID(required=True)
    author_name   = columns.Text(default='')
    author_avatar = columns.Text(default='')
    content       = columns.Text(default='')
    is_deleted    = columns.Boolean(default=False)

    __table_name__ = 'post_comments'

    class Meta:
        get_pk_field = 'uid'
