from rest_framework import serializers

class AuthResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
