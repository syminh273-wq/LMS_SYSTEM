from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class QuizCollection(BaseTimeStampModel):
    """
    Teacher-owned group of Quizzes. Lives in the teacher's global library.
    Assigned to classrooms via QuizCollectionAssignment.

    Items are embedded directly as `item_quiz_ids` (ordered list of quiz
    UUIDs).  The previous standalone `quiz_collection_items` table has
    been removed — items are now a denormalized list on the collection
    row to keep all read paths single-partition.
    """
    uid = columns.UUID(primary_key=True, default=uuid7)

    created_by = columns.UUID(index=True, required=True)
    title = columns.Text(required=True)
    description = columns.Text(default='')
    quiz_count = columns.Integer(default=0)
    certificate_id = columns.UUID(index=True, required=False)
    status = columns.Text(default='draft')

    item_quiz_ids = columns.List(columns.UUID, default=list)

    __table_name__ = 'quiz_collections'

    class Meta:
        get_pk_field = 'uid'
