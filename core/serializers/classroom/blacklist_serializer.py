from rest_framework import serializers


class BlacklistEntrySerializer(serializers.Serializer):
    scope_id     = serializers.UUIDField(read_only=True)
    consumer_uid = serializers.UUIDField(read_only=True)
    scope        = serializers.CharField(read_only=True)
    reason       = serializers.CharField(read_only=True)
    added_by     = serializers.UUIDField(read_only=True)
    created_at   = serializers.DateTimeField(read_only=True)


class BlacklistRequestSerializer(serializers.Serializer):
    consumer_uid = serializers.UUIDField()
    reason       = serializers.CharField(required=False, allow_blank=True, default='')
