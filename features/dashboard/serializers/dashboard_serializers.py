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


class _TopClassSerializer(serializers.Serializer):
    uid = serializers.CharField()
    name = serializers.CharField()
    students = serializers.IntegerField()
    max = serializers.IntegerField()
    submissions = serializers.IntegerField()
    progress = serializers.IntegerField()


class DashboardSummaryResponseSerializer(serializers.Serializer):
    kpis = _KpiSerializer()
    top_classes = _TopClassSerializer(many=True)
