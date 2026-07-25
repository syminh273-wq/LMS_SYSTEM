from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class QuizLeaderboardAttemptSerializer(serializers.Serializer):
    attempt_uid = serializers.CharField(allow_null=True)
    attempt_number = serializers.IntegerField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    score_pct = serializers.IntegerField()
    time_taken_seconds = serializers.IntegerField()
    submitted_at = VnDateTimeField(allow_null=True)


class QuizLeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    student_avatar = serializers.CharField(allow_blank=True)
    best_score_pct = serializers.IntegerField()
    best_score = serializers.IntegerField()
    best_total_questions = serializers.IntegerField()
    best_time_taken_seconds = serializers.IntegerField()
    best_attempt_uid = serializers.CharField(allow_null=True)
    best_attempt_number = serializers.IntegerField()
    best_submitted_at = VnDateTimeField(allow_null=True)
    attempts_count = serializers.IntegerField()


class QuizLeaderboardMeSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    best_score_pct = serializers.IntegerField()
    best_time_taken_seconds = serializers.IntegerField()
    best_attempt_uid = serializers.CharField(allow_null=True)
    attempts_count = serializers.IntegerField()


class QuizLeaderboardResponseSerializer(serializers.Serializer):
    quiz_id = serializers.CharField()
    classroom_id = serializers.CharField()
    total_students = serializers.IntegerField()
    top_3 = QuizLeaderboardEntrySerializer(many=True)
    entries = QuizLeaderboardEntrySerializer(many=True)
    me = QuizLeaderboardMeSerializer(allow_null=True)


class QuizLeaderboardStudentDetailSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    student_avatar = serializers.CharField(allow_blank=True)
    rank = serializers.IntegerField(allow_null=True)
    best_score_pct = serializers.IntegerField()
    best_time_taken_seconds = serializers.IntegerField()
    best_attempt_uid = serializers.CharField(allow_null=True)
    attempts_count = serializers.IntegerField()
    attempts = QuizLeaderboardAttemptSerializer(many=True)
