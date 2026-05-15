from rest_framework import serializers

class ClassroomRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    max_students = serializers.IntegerField(required=False, default=0)
    status = serializers.CharField(required=False, default='active')
