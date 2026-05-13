from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser


class Serializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    avatar_url = serializers.SerializerMethodField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_avatar_url(self, obj):
        if not obj.avatar_url:
            return ""
        from core.storages.storage_service import storage_service
        return storage_service.get_public_url(obj.avatar_url)


class CreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255, required=False, default='')
    phone = serializers.CharField(max_length=20, required=False, default='')
    avatar_url = serializers.CharField(required=False, default='')

    def validate_email(self, value):
        from features.account.consumer.models import Consumer
        if Consumer.objects.filter(email=value, is_deleted=False).allow_filtering().first():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate_username(self, value):
        from features.account.consumer.models import Consumer
        if Consumer.objects.filter(username=value, is_deleted=False).allow_filtering().first():
            raise serializers.ValidationError('Username already taken.')
        return value


class UpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    avatar_url = serializers.CharField(required=False)

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            'invalid': 'Invalid email format.',
            'blank': 'Email cannot be blank.',
            'required': 'Email is required.'
        }
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={
            'blank': 'Password cannot be blank.',
            'required': 'Password is required.'
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            'blank': 'Confirm password cannot be blank.',
            'required': 'Confirm password is required.'
        }
    )
    avatar = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Avatar image file"
    )

    def validate_email(self, value):
        from features.account.consumer.models import Consumer
        if Consumer.objects.filter(email=value, is_deleted=False).allow_filtering().first():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError('Passwords do not match.')
        return attrs

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
