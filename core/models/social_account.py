from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialAccount(BaseTimeStampModel):
    """Lưu liên kết giữa external OAuth provider và user nội bộ."""

    __table_name__ = 'core_social_accounts'

    provider = columns.Text(primary_key=True)       # partition key, e.g. 'google'
    provider_id = columns.Text(primary_key=True)    # clustering key = Google's sub
    user_uid = columns.UUID(index=True)
    user_type = columns.Text(index=True)            # 'consumer' | 'space'
    email = columns.Text(index=True)

    class Meta:
        get_pk_field = 'provider_id'
