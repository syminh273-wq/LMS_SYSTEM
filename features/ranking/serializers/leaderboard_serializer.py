from rest_framework import serializers


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    student_avatar = serializers.CharField(allow_blank=True, required=False, default='')
    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()


class LeaderboardResponseSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_students = serializers.IntegerField()
    entries = LeaderboardEntrySerializer(many=True)


class MyRankSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()
    student_id = serializers.CharField()
