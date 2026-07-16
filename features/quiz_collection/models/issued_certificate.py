from datetime import datetime

from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class IssuedCertificate(BaseTimeStampModel):
    """
    A certificate actually issued to a student after completing a collection
    inside a specific classroom. One row per (collection, classroom, student).
    """
    student_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    certificate_id = columns.UUID(index=True, required=True)
    collection_id = columns.UUID(index=True, required=True)
    classroom_id = columns.UUID(index=True, required=True)
    issued_by = columns.UUID(required=True)
    issued_at = columns.DateTime(default=datetime.now)
    pdf_url = columns.Text(required=False)
    verification_code = columns.Text(required=True, index=True)

    __table_name__ = 'issued_certificates'

    class Meta:
        get_pk_field = 'uid'
