"""DRF serializers for the Space dashboard summary endpoint."""

from rest_framework import serializers


class _KpiSerializer(serializers.Serializer):
    total_classrooms = serializers.IntegerField()
    active_classrooms = serializers.IntegerField()
    total_students = serializers.IntegerField()
    completion_rate_pct = serializers.FloatField()
    certificates_issued = serializers.IntegerField()
    exams_published = serializers.IntegerField()
    submissions = serializers.IntegerField()
    graded = serializers.IntegerField()


class _WeeklyTrendPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    weekday = serializers.CharField()
    enrolled = serializers.IntegerField()
    submitted = serializers.IntegerField()


class _TopClassSerializer(serializers.Serializer):
    uid = serializers.CharField()
    name = serializers.CharField()
    students = serializers.IntegerField()
    max = serializers.IntegerField()
    submissions = serializers.IntegerField()
    progress = serializers.IntegerField()


class _ActivityLogSerializer(serializers.Serializer):
    uid = serializers.CharField()
    log_level = serializers.CharField()
    event_type = serializers.CharField()
    actor_id = serializers.CharField()
    actor_name = serializers.CharField(allow_blank=True)
    actor_role = serializers.CharField(allow_blank=True)
    target_id = serializers.CharField(allow_null=True, required=False)
    target_name = serializers.CharField(allow_blank=True)
    metadata = serializers.DictField(required=False)
    created_at = serializers.CharField(allow_null=True, required=False)


class DashboardSummaryResponseSerializer(serializers.Serializer):
    kpis = _KpiSerializer()
    weekly_trend = _WeeklyTrendPointSerializer(many=True)
    top_classes = _TopClassSerializer(many=True)
    recent_activity = _ActivityLogSerializer(many=True)


class DashboardUsageResponseSerializer(serializers.Serializer):
    storage_used_mb = serializers.IntegerField()
    storage_limit_mb = serializers.IntegerField()
    api_calls_this_month = serializers.IntegerField()
    api_calls_limit = serializers.IntegerField()
    active_classrooms = serializers.IntegerField()
    total_classrooms = serializers.IntegerField()
    published_exams = serializers.IntegerField()
