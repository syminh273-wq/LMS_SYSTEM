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

    exam_id      = columns.UUID(index=True, required=True)
    classroom_id = columns.UUID(index=True, required=True)
    student_id   = columns.UUID(index=True, required=True)

    # ── Submission type ────────────────────────────────────────────────────────
    # "multiple_choice" → ref_id = quiz_plays.uid  (auto-graded MC exam)
    # "online_quiz"     → ref_id = quiz_plays.uid  (online session MC exam)
    # "file"            → ref_id = resource.uid    (file/pdf/image upload)
    # "essay"           → ref_id = null            (text answer)
    submission_type = columns.Text(default="file")

    # Polymorphic FK — what it points to depends on submission_type
    ref_id = columns.UUID(required=False)

    # Raw submission content
    # MC / online_quiz : JSON answers {"question_uid": "a", ...}
    # essay            : plain text
    # file             : "" (file is via ref_id → resource)
    content = columns.Text(default="")

    # Structured metadata (JSON)
    # MC / online_quiz : {"correct_count": 7, "total": 10, "score_pct": 70}
    # file             : {"url": "...", "name": "bai.pdf", "size": 2048}
    # essay            : {}
    meta = columns.Text(default="{}")

    status       = columns.Text(default="submitted")
    submitted_at = columns.DateTime(required=True)

    # ── Grading (all types) ────────────────────────────────────────────────────
    grade          = columns.Float(required=False)
    max_grade      = columns.Float(required=False)
    passed         = columns.Boolean(required=False)
    feedback       = columns.Text(default="")
    graded_by      = columns.UUID(required=False)
    graded_at      = columns.DateTime(required=False)
    grading_method = columns.Text(default="manual")
    returned_at    = columns.DateTime(required=False)

    # ── AI grading detail (file / essay only) ─────────────────────────────────
    ai_model      = columns.Text(default="")
    ai_rubric     = columns.Text(default="")
    ai_reason     = columns.Text(default="")
    ai_breakdown  = columns.Text(default="")
    ai_sources    = columns.Text(default="")
    ai_confidence = columns.Float(required=False)

    # ── Anti-cheat flags ──────────────────────────────────────────────────────
    # is_effective: mặc định False; chỉ teacher quyết định bật/tắt.
    #   - student submit bình thường → is_effective=True
    #   - force_submit (quá max_visibility_breaks / max_face_warnings) → is_effective=False
    is_effective = columns.Boolean(default=False)
    force_submitted = columns.Boolean(default=False)
    force_submit_reason = columns.Text(default="")  # 'visibility_breaks_exceeded' | 'face_warnings_exceeded' | ''
    force_submitted_at = columns.DateTime(required=False)

    is_deleted = columns.Boolean(default=False)
    deleted_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = "uid"

    __table_name__ = "course_exam_submissions"
