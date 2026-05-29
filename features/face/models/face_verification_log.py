from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class FaceVerificationLog(DjangoCassandraModel):
    """
    Records each face verification event during an exam session.
    Partition key = exam_id for efficient teacher queries.
    """
    exam_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    student_id = columns.UUID(index=True, required=True)
    camera_open = columns.Boolean(default=False)
    recognized = columns.Boolean(default=False)
    multiple_faces = columns.Boolean(default=False)
    face_count = columns.Integer(default=0)
    similarity = columns.Float(default=0.0)
    verified_at = columns.DateTime(required=False)

    __table_name__ = "face_verification_logs"

    class Meta:
        get_pk_field = "uid"
