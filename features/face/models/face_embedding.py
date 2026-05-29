import json
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class FaceEmbedding(DjangoCassandraModel):
    """
    Stores the face embedding vector for each student (one per student).
    Partition key = student_id so lookup by student is a single partition read.
    """
    student_id = columns.UUID(primary_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    # 512-float vector stored as JSON text
    embedding_json = columns.Text(required=True)
    enrolled_at = columns.DateTime(required=False)
    is_active = columns.Boolean(default=True)

    __table_name__ = "face_embeddings"

    class Meta:
        get_pk_field = "uid"

    def get_embedding(self) -> list[float]:
        return json.loads(self.embedding_json)

    @classmethod
    def set_embedding(cls, embedding: list[float]) -> str:
        return json.dumps(embedding)
