from rest_framework import serializers


class QuizCollectionItemResponseSerializer(serializers.Serializer):
    quiz_id = serializers.UUIDField(read_only=True)
    order = serializers.IntegerField()
    added_at = serializers.DateTimeField(read_only=True)


class QuizCollectionAssignmentResponseSerializer(serializers.Serializer):
    collection_id = serializers.UUIDField(read_only=True)
    classroom_id = serializers.UUIDField(read_only=True)
    assigned_by = serializers.UUIDField(read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)


class QuizCollectionResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    created_by = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    quiz_count = serializers.IntegerField()
    certificate_id = serializers.UUIDField(allow_null=True, required=False)
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class QuizCollectionDetailResponseSerializer(QuizCollectionResponseSerializer):
    items = QuizCollectionItemResponseSerializer(many=True)
    assignments = QuizCollectionAssignmentResponseSerializer(many=True)


class QuizCollectionProgressResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    passed = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    percent = serializers.FloatField()
    passed_quiz_ids = serializers.ListField(child=serializers.UUIDField())
    missing_quiz_ids = serializers.ListField(child=serializers.UUIDField())
