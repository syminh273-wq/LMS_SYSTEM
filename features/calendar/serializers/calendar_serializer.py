from rest_framework import serializers

class CalendarEventSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    classroom_id = serializers.UUIDField(required=False, allow_null=True)
    space_id = serializers.UUIDField(read_only=True)
    owner_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

class CalendarEventCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['class', 'exam', 'deadline', 'study_session'])
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    classroom_id = serializers.UUIDField(required=False, allow_null=True)
