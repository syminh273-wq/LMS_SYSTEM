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
    full_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=''
    )
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

    def validate_email(self, value):
        from features.account.consumer.models import Consumer
        if Consumer.objects.filter(email=value, is_deleted=False).allow_filtering().first():
            raise serializers.ValidationError('Email already registered.')
        return value

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
