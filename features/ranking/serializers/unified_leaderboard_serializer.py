from rest_framework import serializers


class UnifiedLeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    student_avatar = serializers.CharField(allow_blank=True, required=False, default='')

    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()
    level_title = serializers.CharField()

    total_score = serializers.FloatField()
    quiz_avg = serializers.FloatField()
    exam_avg = serializers.FloatField()
    quiz_count = serializers.IntegerField()
    exam_count = serializers.IntegerField()
    attendance_pct = serializers.FloatField()

    explanation = serializers.CharField(allow_blank=True, required=False, default='')


class UnifiedLeaderboardResponseSerializer(serializers.Serializer):
    classroom_uid = serializers.CharField()
    total_students = serializers.IntegerField()
    my_rank = serializers.IntegerField(allow_null=True, required=False)
    my_score = serializers.FloatField(allow_null=True, required=False)
    my_xp = serializers.IntegerField(allow_null=True, required=False, default=0)
    entries = UnifiedLeaderboardEntrySerializer(many=True)


class StudentClassroomStatsSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    classroom_uid = serializers.CharField()
    student_name = serializers.CharField(allow_blank=True, required=False, default='')
    student_avatar = serializers.CharField(allow_blank=True, required=False, default='')

    rank = serializers.IntegerField(allow_null=True, required=False)
    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()
    level_title = serializers.CharField()

    total_score = serializers.FloatField()
    quiz_avg = serializers.FloatField()
    exam_avg = serializers.FloatField()
    quiz_count = serializers.IntegerField()
    exam_count = serializers.IntegerField()
    attendance_pct = serializers.FloatField()

    explanation = serializers.CharField(allow_blank=True, required=False, default='')
