from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class QuizCollectionAssignment(BaseTimeStampModel):
    """
    Links a teacher-owned QuizCollection to a Classroom.
    Primary key ((collection_id), classroom_id).
    """
    collection_id = columns.UUID(partition_key=True, required=True)
    classroom_id = columns.UUID(primary_key=True, clustering_order="ASC", required=True)

    assigned_by = columns.UUID(required=True)

    __table_name__ = 'quiz_collection_assignments'

    class Meta:
        get_pk_field = 'collection_id'
