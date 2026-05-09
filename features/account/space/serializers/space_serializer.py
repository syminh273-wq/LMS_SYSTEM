from rest_framework import serializers


class Serializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    owner_uid = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField()
    logo_url = serializers.CharField()
    cover_url = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    description = serializers.CharField(required=False, default='')
    logo_url = serializers.URLField(required=False, default='')
    cover_url = serializers.URLField(required=False, default='')

    def validate_slug(self, value):
        from features.account.space.models import Space
        if Space.objects.filter(slug=value, is_deleted=False).allow_filtering().first():
            raise serializers.ValidationError('Slug already taken.')
        return value


class UpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    logo_url = serializers.URLField(required=False)
    cover_url = serializers.URLField(required=False)
