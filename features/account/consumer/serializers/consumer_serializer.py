from rest_framework import serializers


class Serializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    avatar_url = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255, required=False, default='')
    phone = serializers.CharField(max_length=20, required=False, default='')
    avatar_url = serializers.URLField(required=False, default='')

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
    avatar_url = serializers.URLField(required=False)

class RegisterSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
