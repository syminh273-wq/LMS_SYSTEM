from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialProfile(BaseTimeStampModel):
    """
    Social identity + counters — single table for both Consumer and Space.
    Partition by owner_id → fast read for one user.

    Profile data (bio, major, skills, github, linkedin, website) đã chuyển sang
    PortfolioService.get_social_profile() — xem features/portfolio/services/portfolio_service.py.
    """

    owner_id     = columns.UUID(primary_key=True, required=True)

    owner_type   = columns.Text(required=True)
    avatar_url   = columns.Text(default='')
    cover_url    = columns.Text(default='')

    posts_count      = columns.Integer(default=0)
    followers_count  = columns.Integer(default=0)
    following_count  = columns.Integer(default=0)

    __table_name__ = 'user_profiles'

    class Meta:
        get_pk_field = 'owner_id'
