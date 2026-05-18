from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ExamSubmission(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)

    uid = columns.UUID(
        primary_key=True,
        default=uuid7,
        clustering_order="DESC",
    )

    exam_id = columns.UUID(index=True, required=True)
    classroom_id = columns.UUID(index=True, required=True)
    student_id = columns.UUID(index=True, required=True)

    content_type = columns.Text(required=True)
    content = columns.Text(default="")

    resource_uid = columns.UUID(required=False)
    resource_url = columns.Text(default="")
    resource_name = columns.Text(default="")

    status = columns.Text(default="submitted")
    submitted_at = columns.DateTime(required=True)

    grade = columns.Float(required=False)
    feedback = columns.Text(default="")
    graded_by = columns.UUID(required=False)
    graded_at = columns.DateTime(required=False)

    is_deleted = columns.Boolean(default=False)
    deleted_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = "uid"

    __table_name__ = "course_exam_submissions"
