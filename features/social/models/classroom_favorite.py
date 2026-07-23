from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class ClassroomFavorite(BaseTimeStampModel):
    """
    A consumer (student) marks a classroom as favorite.

    Partition by consumer_uid so we can fetch the favorite list for a user
    with a single partition scan. Clustering DESC by classroom_uid keeps
    newest favorites first.
    """

    consumer_uid  = columns.UUID(partition_key=True, required=True)
    classroom_uid = columns.UUID(primary_key=True, clustering_order='DESC', required=True)

    __table_name__ = 'classroom_favorites'

    class Meta:
        get_pk_field = 'classroom_uid'
