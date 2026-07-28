from cassandra.cqlengine import columns
from core.models.cassandra import BaseCassandraModel


class UserSetting(BaseCassandraModel):
    """Per-user key-value settings (notification prefs, theme, etc.).

    Composite primary key: (user_id partition, key clustering).
    django_cassandra_engine requires get_pk_field on composite-key
    models for .get(pk=...) routing; user_id is the natural partition.
    """

    __table_name__ = 'user_settings'

    user_id   = columns.UUID(partition_key=True, primary_key=True, required=True)
    key       = columns.Text(primary_key=True, required=True)

    user_type = columns.Text(required=True, index=True)
    value     = columns.Text()

    class Meta:
        get_pk_field = 'user_id'
