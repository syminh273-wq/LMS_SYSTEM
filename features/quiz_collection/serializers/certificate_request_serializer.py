from rest_framework import serializers


def _validate_template_url(value):
    if not value:
        return value
    if not (value.startswith('http://') or value.startswith('https://')):
        raise serializers.ValidationError('Enter a valid URL.')
    return value


class CertificateCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    template_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None,
    )
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_template_url(self, value):
        return _validate_template_url(value)


class CertificateUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    template_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
    )
    is_active = serializers.BooleanField(required=False)

    def validate_template_url(self, value):
        return _validate_template_url(value)
