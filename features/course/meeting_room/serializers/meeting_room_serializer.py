from rest_framework import serializers

class MeetingRoomSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    classroom_uid = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    host_id = serializers.UUIDField(read_only=True)
    host_type = serializers.CharField(read_only=True)
    host_name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    max_participants = serializers.IntegerField(default=0)
    participant_count = serializers.IntegerField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    ended_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

class CreateMeetingRoomRequest(serializers.Serializer):
    classroom_uid = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    max_participants = serializers.IntegerField(default=0, min_value=0)
