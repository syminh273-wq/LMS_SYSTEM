from rest_framework import serializers


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    student_avatar = serializers.CharField(allow_blank=True, required=False, default='')
    total_score = serializers.FloatField()
    quiz_avg = serializers.FloatField()
    exam_avg = serializers.FloatField()
    quiz_count = serializers.IntegerField()
    exam_count = serializers.IntegerField()
    attendance_pct = serializers.FloatField()


class LeaderboardResponseSerializer(serializers.Serializer):
    classroom_uid = serializers.CharField()
    total_students = serializers.IntegerField()
    my_rank = serializers.IntegerField(allow_null=True)
    my_score = serializers.FloatField(allow_null=True)
    entries = LeaderboardEntrySerializer(many=True)
