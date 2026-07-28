from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class SocialAccount(BaseTimeStampModel):
    """Link between external OAuth provider and internal user.

    Composite primary key: (provider partition, provider_id clustering).
    django_cassandra_engine requires get_pk_field on composite-key
    models so .get(pk=...) and admin lookups can route to a single
    column; provider is the natural routing key.
    """

    __table_name__ = 'core_social_accounts'

    provider    = columns.Text(primary_key=True, required=True)
    provider_id = columns.Text(primary_key=True, required=True)

    user_uid  = columns.UUID(index=True)
    user_type = columns.Text(index=True)
    email     = columns.Text(index=True)

    class Meta:
        get_pk_field = 'provider'
