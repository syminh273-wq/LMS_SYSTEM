from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class XPRule(DjangoCassandraModel):
    """Configurable XP rewards per event type. Single partition (bucket=0).

    Set `is_active=False` to disable awarding for that event without
    deleting the row.
    """

    bucket = columns.Integer(partition_key=True, default=0)
    event_type = columns.Text(primary_key=True, required=True)

    xp_amount = columns.Integer(required=True)
    is_active = columns.Boolean(default=True)
    description = columns.Text(default='')

    class Meta:
        get_pk_field = 'event_type'

    __table_name__ = 'ranking_xp_rules'

    @property
    def pk(self):
        return self.event_type

    @property
    def id(self):
        return self.event_type
