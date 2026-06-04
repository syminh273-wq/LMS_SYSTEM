from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class QuizPlay(DjangoCassandraModel):
    """
    One student play session for a quiz (casual game OR linked from a formal exam).

    Composite partition key (quiz_id, classroom_id) scopes every query
    to a single classroom. Clustering: student_id ASC, uid DESC (newest first).

    When this record is the result of a formal exam submission,
    ExamSubmission.ref_id → this uid.
    """
    quiz_id      = columns.UUID(partition_key=True, required=True)
    classroom_id = columns.UUID(partition_key=True, required=True)
    student_id   = columns.UUID(primary_key=True, clustering_order="ASC", required=True)
    uid          = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    attempt_number     = columns.Integer(default=1)
    score              = columns.Integer(default=0)   # correct_count
    total_questions    = columns.Integer(default=0)
    score_pct          = columns.Integer(default=0)
    time_taken_seconds = columns.Integer(default=0)
    answers            = columns.Map(columns.Text, columns.Text, default={})
    submitted_at       = columns.DateTime(default=datetime.now)

    __table_name__ = 'quiz_plays'

    class Meta:
        get_pk_field = 'uid'
