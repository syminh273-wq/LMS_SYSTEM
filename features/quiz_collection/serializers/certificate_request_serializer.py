from rest_framework import serializers


class CertificateCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    template_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)


class CertificateUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    template_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False)
