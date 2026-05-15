from rest_framework import serializers

class ResourceResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    file_type = serializers.CharField()
    url = serializers.CharField()
    size = serializers.IntegerField()
    owner_id = serializers.UUIDField(read_only=True)
    owner_type = serializers.CharField(read_only=True)
    metadata = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
