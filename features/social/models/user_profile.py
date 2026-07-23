from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class UserProfile(BaseTimeStampModel):
    """
    Community Workspace user profile — single table for both Consumer and Space.
    Partition by owner_id → fast read for one user.
    Bucket 0 enables global queries (e.g. for discovery).
    """

    bucket       = columns.Integer(partition_key=True, default=0)
    owner_id     = columns.UUID(primary_key=True, required=True)

    owner_type   = columns.Text(required=True)        # 'consumer' | 'space'
    avatar_url   = columns.Text(default='')
    cover_url    = columns.Text(default='')
    bio          = columns.Text(default='')
    major        = columns.Text(default='')
    department   = columns.Text(default='')
    skills       = columns.List(columns.Text, default=list)
    github       = columns.Text(default='')
    linkedin     = columns.Text(default='')
    website      = columns.Text(default='')

    posts_count      = columns.Integer(default=0)
    followers_count  = columns.Integer(default=0)
    following_count  = columns.Integer(default=0)

    __table_name__ = 'user_profiles'

    class Meta:
        get_pk_field = 'owner_id'
