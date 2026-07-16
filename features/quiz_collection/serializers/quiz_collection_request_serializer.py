from rest_framework import serializers


class QuizCollectionCreateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    certificate_id = serializers.UUIDField(required=False, allow_null=True)


class QuizCollectionUpdateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=['draft', 'published', 'archived'], required=False)
    certificate_id = serializers.UUIDField(required=False, allow_null=True)


class QuizCollectionAddItemsRequestSerializer(serializers.Serializer):
    quiz_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50,
    )


class QuizCollectionReorderRequestSerializer(serializers.Serializer):
    ordered_quiz_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
    )


class QuizCollectionAssignRequestSerializer(serializers.Serializer):
    classroom_id = serializers.UUIDField(required=True)
