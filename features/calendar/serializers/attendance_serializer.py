from rest_framework import serializers

class AttendanceSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    status = serializers.CharField()
    joined_at = serializers.DateTimeField(required=False, allow_null=True)
    left_at = serializers.DateTimeField(required=False, allow_null=True)
    date = serializers.DateField()

class AttendanceUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['present', 'absent', 'late', 'excused'])
