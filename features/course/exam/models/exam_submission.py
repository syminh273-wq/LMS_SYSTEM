from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ExamSubmission(BaseTimeStampModel):
    uid = columns.UUID(
        primary_key=True,
        default=uuid7,
    )

    exam_id      = columns.UUID(index=True, required=True)
    classroom_id = columns.UUID(index=True, required=True)
    student_id   = columns.UUID(index=True, required=True)
    submission_type = columns.Text(default="file")
    ref_id = columns.UUID(required=False)

    content = columns.Text(default="")


    meta = columns.Text(default="{}")

    status       = columns.Text(default="submitted")
    submitted_at = columns.DateTime(required=True)

    grade          = columns.Float(required=False)
    max_grade      = columns.Float(required=False)
    passed         = columns.Boolean(required=False)
    feedback       = columns.Text(default="")
    graded_by      = columns.UUID(required=False)
    graded_at      = columns.DateTime(required=False)
    grading_method = columns.Text(default="manual")
    returned_at    = columns.DateTime(required=False)

    ai_model      = columns.Text(default="")
    ai_rubric     = columns.Text(default="")
    ai_reason     = columns.Text(default="")
    ai_breakdown  = columns.Text(default="")
    ai_sources    = columns.Text(default="")
    ai_confidence = columns.Float(required=False)


    is_effective = columns.Boolean(default=False)
    force_submitted = columns.Boolean(default=False)
    force_submit_reason = columns.Text(default="")
    force_submitted_at = columns.DateTime(required=False)

    is_deleted = columns.Boolean(default=False)
    deleted_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = "uid"

    __table_name__ = "course_exam_submissions"
