from rest_framework import serializers


class AchievementSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    icon = serializers.CharField()
    target_value = serializers.IntegerField()
    current_value = serializers.IntegerField()
    progress_pct = serializers.IntegerField()
    is_unlocked = serializers.BooleanField()
    unlocked_at = serializers.CharField(allow_null=True, required=False)
