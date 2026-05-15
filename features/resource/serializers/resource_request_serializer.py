from rest_framework import serializers

class ResourceRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    metadata = serializers.DictField(required=False)
