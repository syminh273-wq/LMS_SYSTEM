from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class QuizCollection(BaseTimeStampModel):
    """
    Teacher-owned group of Quizzes. Lives in the teacher's global library.
    Assigned to classrooms via QuizCollectionAssignment.
    """
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    created_by = columns.UUID(index=True, required=True)
    title = columns.Text(required=True)
    description = columns.Text(default='')
    quiz_count = columns.Integer(default=0)
    certificate_id = columns.UUID(index=True, required=False)
    status = columns.Text(default='draft')

    __table_name__ = 'quiz_collections'

    class Meta:
        get_pk_field = 'uid'
