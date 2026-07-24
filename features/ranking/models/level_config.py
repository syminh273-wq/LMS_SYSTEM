from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class LevelConfig(DjangoCassandraModel):
    """Static level definitions. Single partition (bucket=0).

    `required_xp` is the cumulative XP needed to *reach* this level.
    Level 1 always has required_xp=0.
    """

    bucket = columns.Integer(partition_key=True, default=0)
    level = columns.Integer(primary_key=True, required=True)

    required_xp = columns.BigInt(required=True)
    title = columns.Text(default='')
    color = columns.Text(default='blue')

    class Meta:
        get_pk_field = 'level'

    __table_name__ = 'ranking_level_configs'

    @property
    def pk(self):
        return self.level

    @property
    def id(self):
        return self.level
