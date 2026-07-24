from rest_framework import serializers


class StudentXPSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()
    current_level_xp = serializers.IntegerField()
    next_level_xp = serializers.IntegerField()
    progress_pct = serializers.IntegerField()
    xp_to_next_level = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    last_active_date = serializers.CharField(allow_null=True, required=False)
    classrooms_joined_count = serializers.IntegerField()
    quizzes_passed_count = serializers.IntegerField()
    exams_passed_count = serializers.IntegerField()
    perfect_scores_count = serializers.IntegerField()
    certificates_count = serializers.IntegerField()
    attendance_count = serializers.IntegerField()
    level_title = serializers.CharField()
