"""Analytics serializers for the space payment dashboard."""

from rest_framework import serializers


class _KpiSerializer(serializers.Serializer):
    total_revenue = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    total_paid_amount = serializers.IntegerField()
    total_pending_amount = serializers.IntegerField()
    refunded_amount = serializers.IntegerField()
    failed_count = serializers.IntegerField()


class _StatusPointSerializer(serializers.Serializer):
    status = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    amount = serializers.IntegerField()
    percentage = serializers.FloatField()


class _RevenueTrendPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    revenue = serializers.IntegerField()
    transaction_count = serializers.IntegerField()


class _ByClassroomSerializer(serializers.Serializer):
    classroom_uid = serializers.CharField()
    classroom_name = serializers.CharField()
    total_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    total_revenue = serializers.IntegerField()


class _FiltersSerializer(serializers.Serializer):
    from_ = serializers.DateTimeField(source='from', allow_null=True, required=False)
    to = serializers.DateTimeField(allow_null=True, required=False)
    status = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    resource_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    bucket = serializers.CharField()


class PaymentAnalyticsResponseSerializer(serializers.Serializer):
    kpis = _KpiSerializer()
    status_distribution = _StatusPointSerializer(many=True)
    revenue_trend = _RevenueTrendPointSerializer(many=True)
    by_classroom = _ByClassroomSerializer(many=True)
    filters = _FiltersSerializer()
    approximated = serializers.BooleanField()
