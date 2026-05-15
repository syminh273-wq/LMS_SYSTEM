from rest_framework import serializers

class ClassroomResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    pid = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    teacher_id = serializers.UUIDField(read_only=True)
    max_students = serializers.IntegerField()
    status = serializers.CharField()
    resolve_link = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
