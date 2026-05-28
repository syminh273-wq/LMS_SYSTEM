from rest_framework import serializers
import json


class ExamSubmissionRequestSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=["markdown", "pdf", "image", "file"])
    content = serializers.CharField(required=False, allow_blank=True)
    resource_uid = serializers.UUIDField(required=False, allow_null=True)


class ExamSubmissionGradeSerializer(serializers.Serializer):
    grade = serializers.FloatField(required=False)
    feedback = serializers.CharField(required=False, allow_blank=True)


class ExamSubmissionAIGradeSerializer(serializers.Serializer):
    rubric = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    max_grade = serializers.FloatField(default=10, min_value=1, max_value=100)
    overwrite = serializers.BooleanField(default=False)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=10)


def _loads_json(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def serialize_exam_submission(submission):
    return {
        "uid": str(submission.uid),
        "exam_id": str(submission.exam_id),
        "classroom_id": str(submission.classroom_id),
        "student_id": str(submission.student_id),
        "content_type": submission.content_type,
        "content": submission.content,
        "resource_uid": str(submission.resource_uid) if submission.resource_uid else None,
        "resource_url": submission.resource_url,
        "resource_name": submission.resource_name,
        "status": submission.status,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "grade": submission.grade,
        "feedback": submission.feedback,
        "graded_by": str(submission.graded_by) if submission.graded_by else None,
        "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
        "grading_method": getattr(submission, "grading_method", "manual") or "manual",
        "ai_model": getattr(submission, "ai_model", "") or "",
        "ai_rubric": getattr(submission, "ai_rubric", "") or "",
        "ai_reason": getattr(submission, "ai_reason", "") or "",
        "ai_breakdown": _loads_json(getattr(submission, "ai_breakdown", ""), []),
        "ai_sources": _loads_json(getattr(submission, "ai_sources", ""), []),
        "ai_confidence": getattr(submission, "ai_confidence", None),
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
        "updated_at": submission.updated_at.isoformat() if submission.updated_at else None,
    }
