from rest_framework import serializers


class CertificateResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    created_by = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    template_url = serializers.CharField(allow_null=True, required=False)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
