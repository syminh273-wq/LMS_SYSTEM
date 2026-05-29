from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class ClassroomActivityLog(DjangoCassandraModel):
    """
    Activity log for all events that happen inside a classroom.

    Partition key = classroom_uid  → efficient "all events for classroom X" queries.
    Clustering    = created_at DESC, uid  → newest-first, unique per row.

    log_level:
        "major"  – teacher-visible events (document added, exam opened, member approved…)
        "detail" – audit-trail events (who joined when, who submitted…)

    event_type (major):
        classroom_created | document_uploaded | exam_created | exam_published |
        exam_opened | exam_closed | quiz_assigned | meeting_started | meeting_ended |
        member_approved

    event_type (detail):
        member_joined | member_rejected | member_kicked | member_left |
        exam_submitted | document_deleted | exam_deleted
    """

    classroom_uid = columns.UUID(partition_key=True, required=True)
    created_at    = columns.DateTime(primary_key=True, clustering_order='DESC', default=datetime.utcnow)
    uid           = columns.UUID(primary_key=True, default=uuid7, clustering_order='DESC')

    log_level     = columns.Text(required=True)   # "major" | "detail"
    event_type    = columns.Text(required=True)

    actor_id      = columns.UUID(required=True)
    actor_name    = columns.Text(default='')
    actor_role    = columns.Text(default='')      # "teacher" | "student" | "system"

    target_id     = columns.UUID(required=False)
    target_name   = columns.Text(default='')      # snapshot: exam title, filename, member name…

    metadata      = columns.Text(default='{}')    # JSON string for extra context

    __table_name__ = 'classroom_activity_logs'

    class Meta:
        get_pk_field = 'uid'
