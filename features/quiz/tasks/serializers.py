from rest_framework import serializers


class QuizGenerateTaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()


class QuizTaskStatusResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.DictField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)


class QuizTaskListItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    kind = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    progress = serializers.IntegerField(required=False, default=0)
    current_step = serializers.IntegerField(required=False, default=0)
    total_steps = serializers.IntegerField(required=False, default=0)
    quiz_uid = serializers.CharField(required=False, allow_null=True, default=None)
    error_message = serializers.CharField(required=False, allow_null=True, default=None)
    created_at = serializers.CharField(required=False, allow_blank=True)
    updated_at = serializers.CharField(required=False, allow_blank=True)
    completed_at = serializers.CharField(required=False, allow_null=True, default=None)
