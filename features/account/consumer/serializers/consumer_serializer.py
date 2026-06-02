from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from features.account.consumer.models.consumer import Consumer

class ConsumerAccountSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    pid = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    full_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    avatar_url = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_avatar_url(self, obj):
        if not obj.avatar_url:
            return ""
        from core.storages.storage_service import storage_service
        return storage_service.get_public_url(obj.avatar_url)

class ConsumerAccountCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True, default='')

class ConsumerAccountUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    avatar_url = serializers.CharField(required=False, allow_blank=True)

class ConsumerAccountLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ConsumerChangePasswordSerializer(serializers.Serializer):
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
