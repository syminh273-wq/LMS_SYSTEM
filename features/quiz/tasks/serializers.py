from rest_framework import serializers


class QuizGenerateTaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()


class QuizTaskStatusResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.DictField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)
