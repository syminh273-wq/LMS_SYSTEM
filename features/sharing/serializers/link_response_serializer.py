from rest_framework import serializers

class LinkResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    code = serializers.CharField()
    resource_type = serializers.CharField()
    resource_id = serializers.UUIDField()
    action = serializers.CharField()
    expired_at = serializers.DateTimeField()
    max_usage = serializers.IntegerField()
    used_count = serializers.IntegerField()
    is_active = serializers.BooleanField()
    metadata = serializers.DictField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
