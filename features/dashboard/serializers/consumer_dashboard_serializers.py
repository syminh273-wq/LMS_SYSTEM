from rest_framework import serializers

from core.serializers.fields import VnDateTimeField
from features.quiz_collection.serializers.issued_certificate_response_serializer import (
    IssuedCertificateResponseSerializer,
)


class _GpaSerializer(serializers.Serializer):
    gpa_4 = serializers.FloatField()
    avg_10 = serializers.FloatField()


class _ScheduleItemSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField()
    start_time = VnDateTimeField()
    end_time = VnDateTimeField()
    classroom_id = serializers.UUIDField(required=False, allow_null=True)


class _RecentGradeSerializer(serializers.Serializer):
    submission_uid = serializers.CharField()
    exam_title = serializers.CharField(allow_blank=True)
    classroom_name = serializers.CharField(allow_blank=True)
    grade = serializers.FloatField()
    max_grade = serializers.FloatField()
    percent = serializers.FloatField()
    graded_at = VnDateTimeField(allow_null=True)


class ConsumerDashboardSummaryResponseSerializer(serializers.Serializer):
    gpa = _GpaSerializer()
    active_classrooms = serializers.IntegerField()
    assignments_submitted = serializers.IntegerField()
    assignments_total = serializers.IntegerField()
    attendance_pct = serializers.FloatField()
    today_schedule = _ScheduleItemSerializer(many=True)
    recent_grades = _RecentGradeSerializer(many=True)
    recent_certificates = IssuedCertificateResponseSerializer(many=True)
