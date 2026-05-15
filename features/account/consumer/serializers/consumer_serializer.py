from rest_framework import serializers
from features.account.consumer.models.consumer import Consumer

class ConsumerAccountSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField()
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
    full_name = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(required=False, allow_blank=True, default='')

class ConsumerAccountUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    avatar_url = serializers.CharField(required=False, allow_blank=True)

class ConsumerAccountLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
