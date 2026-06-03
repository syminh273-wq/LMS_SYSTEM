import json

from rest_framework import serializers


class ExamSubmissionRequestSerializer(serializers.Serializer):
    submission_type = serializers.ChoiceField(
        choices=["multiple_choice", "online_quiz", "file", "essay"],
        required=False,
        default="online_quiz",
    )
    ref_id          = serializers.UUIDField(required=False, allow_null=True)
    answers         = serializers.DictField(child=serializers.CharField(), required=False)
    content         = serializers.CharField(required=False, allow_blank=True)
    time_taken_seconds = serializers.IntegerField(required=False, default=0)


class ExamSubmissionGradeSerializer(serializers.Serializer):
    grade    = serializers.FloatField(required=False)
    feedback = serializers.CharField(required=False, allow_blank=True)


class ExamSubmissionAIGradeSerializer(serializers.Serializer):
    rubric     = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    max_grade  = serializers.FloatField(default=10, min_value=1, max_value=100)
    overwrite  = serializers.BooleanField(default=False)
    top_k      = serializers.IntegerField(default=5, min_value=1, max_value=10)


def _load(value, fallback=None):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def serialize_exam_submission(submission):
    meta = _load(submission.meta, {})
    submission_type = getattr(submission, "submission_type", "file") or "file"
    is_mc = submission_type in ("multiple_choice", "online_quiz")

    return {
        "uid":         str(submission.uid),
        "exam_id":     str(submission.exam_id),
        "classroom_id": str(submission.classroom_id),
        "student_id":  str(submission.student_id),

        "submission_type": submission_type,
        "ref_id": str(submission.ref_id) if submission.ref_id else None,
        "content": submission.content,
        "meta": meta,

        # Convenience fields derived from meta — keeps backward compat
        "resource_url":  meta.get("url") if not is_mc else None,
        "resource_name": meta.get("name") if not is_mc else None,
        "quiz_result": {
            "correct_count": meta.get("correct_count", 0),
            "total":         meta.get("total", 0),
            "score_pct":     meta.get("score_pct", 0),
            "results":       meta.get("results", []),
        } if is_mc else None,

        "status":       submission.status,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,

        # Grading
        "grade":          submission.grade,
        "max_grade":      getattr(submission, "max_grade", None),
        "passed":         getattr(submission, "passed", None),
        "feedback":       submission.feedback,
        "graded_by":      str(submission.graded_by) if submission.graded_by else None,
        "graded_at":      submission.graded_at.isoformat() if submission.graded_at else None,
        "grading_method": getattr(submission, "grading_method", "manual") or "manual",
        "returned_at":    submission.returned_at.isoformat() if getattr(submission, "returned_at", None) else None,

        # AI detail
        "ai_model":      getattr(submission, "ai_model", "") or "",
        "ai_rubric":     getattr(submission, "ai_rubric", "") or "",
        "ai_reason":     getattr(submission, "ai_reason", "") or "",
        "ai_breakdown":  _load(getattr(submission, "ai_breakdown", ""), []),
        "ai_sources":    _load(getattr(submission, "ai_sources", ""), []),
        "ai_confidence": getattr(submission, "ai_confidence", None),

        "created_at": submission.created_at.isoformat() if submission.created_at else None,
        "updated_at": submission.updated_at.isoformat() if submission.updated_at else None,
    }
