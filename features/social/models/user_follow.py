from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class UserFollow(DjangoCassandraModel):
    """
    Tracks who follows whom.
    Partition by follower_uid -> get all people this user follows.
    Index followed_uid -> get all people following this user.
    """

    follower_uid = columns.UUID(partition_key=True, required=True)
    followed_uid = columns.UUID(primary_key=True, clustering_order='ASC', required=True)
    
    follower_name   = columns.Text(default='')   # snapshot for display
    follower_avatar = columns.Text(default='')
    followed_name   = columns.Text(default='')   # snapshot for display
    followed_avatar = columns.Text(default='')
    
    created_at   = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'user_follows'

    class Meta:
        get_pk_field = 'followed_uid'
