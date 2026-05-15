from rest_framework import serializers

class LinkRequestSerializer(serializers.Serializer):
    code = serializers.CharField(required=False, allow_blank=True)
    resource_type = serializers.CharField(required=True)
    resource_id = serializers.UUIDField(required=True)
    action = serializers.CharField(required=False, allow_blank=True)
    expired_at = serializers.DateTimeField(required=False, allow_null=True)
    max_usage = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)
    metadata = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict
    )
