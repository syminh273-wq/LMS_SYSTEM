from rest_framework import serializers

class NotificationLogSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    target_uid = serializers.UUIDField()
    notify_type = serializers.CharField()
    title = serializers.CharField()
    content = serializers.CharField()
    metadata = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
