from datetime import datetime

from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class QuizCollectionItem(BaseTimeStampModel):
    """
    One Quiz inside a QuizCollection. Composite key keeps ordering.
    """
    collection_id = columns.UUID(partition_key=True, required=True)
    quiz_id = columns.UUID(primary_key=True, clustering_order="ASC", required=True)

    order = columns.Integer(default=0)
    added_at = columns.DateTime(default=datetime.now)

    __table_name__ = 'quiz_collection_items'

    class Meta:
        get_pk_field = 'quiz_id'
