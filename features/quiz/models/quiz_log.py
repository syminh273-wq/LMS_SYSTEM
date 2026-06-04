from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class QuizLog(DjangoCassandraModel):
    """
    One student attempt — covers both casual game and formal exam context.

    source="game" → standalone quiz play, exam_id=null
    source="exam" → quiz within a formal exam, exam_id=exam.uid
                    ExamSubmission.ref_id → this uid
    """
    quiz_id      = columns.UUID(partition_key=True, required=True)
    classroom_id = columns.UUID(partition_key=True, required=True)
    student_id   = columns.UUID(primary_key=True, clustering_order="ASC", required=True)
    uid          = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    source  = columns.Text(default="game")   # "game" | "exam"
    exam_id = columns.UUID(required=False)

    answers            = columns.Map(columns.Text, columns.Text, default={})
    time_taken_seconds = columns.Integer(default=0)
    submitted_at       = columns.DateTime(default=datetime.now)

    attempt_number  = columns.Integer(default=1)
    score           = columns.Integer(default=0)   # correct_count
    total_questions = columns.Integer(default=0)
    score_pct       = columns.Integer(default=0)
    graded_at       = columns.DateTime(required=False)

    __table_name__ = 'quiz_logs'

    class Meta:
        get_pk_field = 'uid'
