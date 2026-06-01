from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from features.account.space.models.space import Space


class CassandraSafeDateField(serializers.DateField):
    def to_representation(self, value):
        if value is None:
            return None
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)


class SpaceAccountSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    full_name = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    logo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    hometown = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = CassandraSafeDateField(required=False, allow_null=True)
    avatar_url = serializers.SerializerMethodField()
    learning_certificates = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )
    contact_information = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_logo_url(self, obj):
        if not obj.logo_url:
            return ""
        from core.storages.storage_service import storage_service
        return storage_service.get_public_url(obj.logo_url)

    def get_cover_url(self, obj):
        if not obj.cover_url:
            return ""
        from core.storages.storage_service import storage_service
        return storage_service.get_public_url(obj.cover_url)

    def get_avatar_url(self, obj):
        if not obj.avatar_url:
            return ""
        from core.storages.storage_service import storage_service
        return storage_service.get_public_url(obj.avatar_url)

class SpaceAccountCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, default='')
    name = serializers.CharField(required=False, allow_blank=True, default='')
    slug = serializers.CharField(required=False, allow_blank=True, default='')

class SpaceAccountUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    logo_url = serializers.CharField(required=False, allow_blank=True)
    cover_url = serializers.CharField(required=False, allow_blank=True)

class SpaceAccountProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    hometown = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    avatar_url = serializers.CharField(required=False, allow_blank=True)
    learning_certificates = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )
    contact_information = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )

    def validate_contact_information(self, value):
        allowed_methods = {'gmail', 'phone', 'zalo'}
        normalized = {}

        for method, contact in value.items():
            normalized_method = str(method).strip().lower()
            if normalized_method not in allowed_methods:
                raise serializers.ValidationError(
                    f"Unsupported contact method '{method}'. Supported methods are Gmail, Phone, and Zalo."
                )
            normalized[normalized_method] = contact

        return normalized

class SpaceChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': ['New password and confirm password do not match.']
            })

        validate_password(new_password)
        return attrs

class SpaceAccountLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
