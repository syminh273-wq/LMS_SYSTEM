from rest_framework import serializers


class AIGradeRequestSerializer(serializers.Serializer):
    rubric = serializers.CharField(required=False, allow_blank=True, default="")


class TeacherGradeRequestSerializer(serializers.Serializer):
    score = serializers.FloatField(required=False, min_value=0)
    grade = serializers.FloatField(required=False, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True)
    ai_grade_uid = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if "score" not in attrs and "grade" not in attrs and "ai_grade_uid" not in attrs:
            raise serializers.ValidationError("score or ai_grade_uid is required")
        if "score" in attrs and "grade" in attrs and attrs["score"] != attrs["grade"]:
            raise serializers.ValidationError("score and grade must match when both are provided")
        return attrs


def serialize_grade(grade):
    return {
        "uid": str(grade.uid),
        "submission_id": str(grade.submission_id),
        "exam_id": str(grade.exam_id),
        "classroom_id": str(grade.classroom_id),
        "student_id": str(grade.student_id),
        "grader_role": grade.grader_role,
        "grader_id": str(grade.grader_id) if grade.grader_id else None,
        "score": grade.score,
        "max_score": grade.max_score,
        "feedback": grade.feedback,
        "status": grade.status,
        "ai_model": grade.ai_model,
        "created_at": grade.created_at.isoformat() if grade.created_at else None,
        "updated_at": grade.updated_at.isoformat() if grade.updated_at else None,
    }
