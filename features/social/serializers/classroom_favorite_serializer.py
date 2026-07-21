from rest_framework import serializers

from core.serializers.classroom.classroom_response_serializer import ClassroomResponseSerializer


class ClassroomFavoriteResponseSerializer(serializers.Serializer):
    classroom = ClassroomResponseSerializer()
    created_at = serializers.DateTimeField()
