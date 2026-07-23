from datetime import datetime
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ConsumerPost(BaseTimeStampModel):
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

    author_type    = columns.Text(default='consumer')  # 'consumer' | 'space'
    space_uid      = columns.UUID(index=True, required=False)  # set when author_type='space'

    content        = columns.Text(default='')
    emotion        = columns.Text(default='')    # happy|sad|motivated|excited|...
    image_url      = columns.Text(default='')    # legacy: first image URL (backward-compat)
    image_urls     = columns.List(columns.Text, default=list)  # full list of image URLs
    visibility     = columns.Text(default='public')  # public|private|friends
    classroom_tags = columns.List(columns.UUID, required=False)

    likes_count    = columns.Integer(default=0)
    comments_count = columns.Integer(default=0)

    __table_name__ = 'consumer_posts'

    class Meta:
        get_pk_field = 'uid'
