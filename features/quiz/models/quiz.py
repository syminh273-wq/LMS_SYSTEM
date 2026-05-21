from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Quiz(BaseTimeStampModel):
    """
    Teacher-owned quiz (master data). Not tied to any classroom.
    Assign to classrooms via QuizAssignment.
    """
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    created_by = columns.UUID(index=True, required=True)   # teacher uid
    resource_id = columns.UUID(index=True)                 # source document (optional)

    title = columns.Text(required=True)
    description = columns.Text(default='')
    questions_count = columns.Integer(default=0)
    status = columns.Text(default='draft')   # draft | published | archived

    __table_name__ = 'quiz_quizzes'

    class Meta:
        get_pk_field = 'uid'
