from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class ClassroomMemberHistorySerializer(serializers.Serializer):
    """Read-only projection of a ClassroomMember row for the consumer join history view."""
    classroom_uid = serializers.SerializerMethodField()
    classroom_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    has_paid = serializers.BooleanField(read_only=True)
    joined_at = VnDateTimeField(read_only=True)
    paid_at = VnDateTimeField(read_only=True)

    def get_classroom_uid(self, obj):
        return str(getattr(obj, 'classroom_uid', ''))

    def get_classroom_name(self, obj):
        return (self.context.get('classroom_name') or '')

    def get_teacher_name(self, obj):
        return (self.context.get('teacher_name') or '')
