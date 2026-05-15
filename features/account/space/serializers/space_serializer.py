from rest_framework import serializers
from features.account.space.models.space import Space

class SpaceAccountSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    full_name = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    logo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
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

class SpaceAccountLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
