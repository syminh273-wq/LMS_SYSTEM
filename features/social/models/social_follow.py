from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialFollow(BaseTimeStampModel):
    """
    Tracks who follows whom (consumer or space).
    Partition by follower_id  →  get all entities this user follows.
    Partition by followed_id  →  get all followers of a user (via second table or query).
    """

    follower_id     = columns.UUID(partition_key=True, required=True)
    follower_type   = columns.Text(default='consumer')
    followed_id     = columns.UUID(primary_key=True, clustering_order='ASC', required=True)
    followed_type   = columns.Text(default='consumer')

    follower_name   = columns.Text(default='')
    follower_avatar = columns.Text(default='')
    followed_name   = columns.Text(default='')
    followed_avatar = columns.Text(default='')

    __table_name__ = 'social_follows'

    class Meta:
        get_pk_field = 'followed_id'
