from rest_framework import serializers


class DummyRequestSerializer(serializers.Serializer):
    """Request serializer — reused for both create and update (PATCH)."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(
        required=False, allow_blank=True, default='',
    )
    status = serializers.CharField(required=False, default='active')
