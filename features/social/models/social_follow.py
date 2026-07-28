from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialFollow(BaseTimeStampModel):
    """
    Tracks who follows whom (consumer or space).
    Partition by uid (follower)  →  get all entities this user follows.
    """

    uid = columns.UUID(partition_key=True, primary_key=True, required=True)
    followed_id = columns.UUID(primary_key=True, clustering_order='ASC', required=True)

    follower_type = columns.Text(default='consumer')
    followed_type = columns.Text(default='consumer')

    __table_name__ = 'social_follows'

    class Meta:
        get_pk_field = 'uid'
