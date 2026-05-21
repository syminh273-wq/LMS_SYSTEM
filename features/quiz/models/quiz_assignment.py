from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class QuizAssignment(BaseTimeStampModel):
    """
    Links a teacher-owned Quiz to a Classroom.
    Partitioned by quiz_id so we can list all classrooms a quiz is assigned to.
    Primary key is ((quiz_id), classroom_id).
    """
    quiz_id = columns.UUID(partition_key=True, required=True)
    classroom_id = columns.UUID(primary_key=True, clustering_order="ASC", required=True)

    assigned_by = columns.UUID(required=True)   # teacher uid
    # assigned_at will use created_at from BaseTimeStampModel
    time_limit_seconds = columns.Integer(default=0)
    max_attempts       = columns.Integer(default=0)
    shuffle_questions  = columns.Boolean(default=False)
    shuffle_options    = columns.Boolean(default=False)
    show_explanation   = columns.Boolean(default=True)
    passing_score_pct  = columns.Integer(default=50)

    __table_name__ = 'quiz_assignments'

    class Meta:
        get_pk_field = 'quiz_id'
