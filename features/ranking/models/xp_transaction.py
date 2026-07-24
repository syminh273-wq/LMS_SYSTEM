from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class XPTransaction(DjangoCassandraModel):
    """Append-only ledger of every XP event for a student.

    Used by:
        - `/me/transactions/`  (paginated history)
        - Idempotency check    (event_type + ref_type + ref_id is unique
                                per student — see XPService)

    Composite primary key: (student_id, uid). `uid` is UUIDv7 so DESC
    ordering naturally gives newest-first.
    """

    student_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    created_at = columns.DateTime(default=datetime.utcnow)

    event_type = columns.Text(required=True, index=True)
    delta_xp = columns.Integer(required=True)

    ref_type = columns.Text(required=False)
    ref_id = columns.UUID(required=False)
    classroom_id = columns.UUID(required=False, index=True)

    description = columns.Text(default='')
    metadata = columns.Text(default='{}')

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'ranking_xp_transactions'

    @property
    def pk(self):
        return self.uid

    @property
    def id(self):
        return self.uid
