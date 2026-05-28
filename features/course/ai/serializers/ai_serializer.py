from rest_framework import serializers


class AIQueryParamSerializer(serializers.Serializer):
    """Query params shared by both /ask and /ingest."""
    classroom_id = serializers.UUIDField(required=False)
    document_id  = serializers.UUIDField(required=False)

    def validate(self, data):
        if not data.get('classroom_id') and not data.get('document_id'):
            raise serializers.ValidationError(
                "At least one of 'classroom_id' or 'document_id' is required."
            )
        return data


class AIAskSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, max_length=2000)
    top_k    = serializers.IntegerField(default=3, min_value=1, max_value=10)


class AIIngestSerializer(serializers.Serializer):
    resource_id = serializers.UUIDField(required=True)
