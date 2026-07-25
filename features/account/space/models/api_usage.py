from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class ApiUsage(DjangoCassandraModel):
    """Tracks API calls per Space account per month.

    Partition key: (space_id, year_month) to ensure efficient
    per-user-per-month queries without scanning.
    """
    __table_name__ = 'account_api_usage'

    space_id = columns.UUID(partition_key=True)
    year_month = columns.Text(partition_key=True)  # "2026-07"
    call_count = columns.Counter()

    class Meta:
        get_pk_field = 'space_id'
