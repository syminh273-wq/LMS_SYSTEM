from rest_framework import serializers

class ResourceQuerySerializer(serializers.Serializer):
    type = serializers.CharField(required=False)
