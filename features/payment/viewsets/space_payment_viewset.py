from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import SpaceScopeMixin
from features.payment.serializers.payment_analytics_serializer import (
    PaymentAnalyticsResponseSerializer,
)
from features.payment.services.payment_analytics_service import (
    PaymentAnalyticsService,
    default_window,
    parse_date_param,
)


class SpacePaymentViewSet(SpaceScopeMixin, ViewSet):
    """Teacher-side payment received view (history of payments for classrooms they own)."""

    def list(self, request):
        """
        List payments received for classrooms this teacher owns.
        @param status: filter by payment status (optional)
        @param limit: max entries, default 50
        @return: list of payments
        """
        teacher_id = request.user.uid
        status_filter = (request.query_params.get('status') or '').strip().lower() or None
        try:
            limit = int(request.query_params.get('limit') or 50)
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))

        from features.payment.repositories import PaymentRepository
        from features.payment.serializers.payment_response_serializer import PaymentResponseSerializer

        payments = list(PaymentRepository().get_by_teacher(teacher_id, status=status_filter, limit=limit))
        return Response(PaymentResponseSerializer(payments, many=True).data)

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Get a payment analytics summary for this teacher, bucketed over time.
        @param from: ISO date range start (optional)
        @param to: ISO date range end (optional)
        @param status: completed|pending|failed|cancelled (optional)
        @param resource_id: classroom uid (optional)
        @param bucket: day|week|month, auto when omitted
        @return: payment analytics summary
        """
        teacher_id = request.user.uid

        from_dt = parse_date_param(request.query_params.get('from'))
        to_dt = parse_date_param(request.query_params.get('to'))
        if not from_dt and not to_dt:
            from_dt, to_dt = default_window(30)

        status_filter = (request.query_params.get('status') or '').strip().lower() or None
        resource_id = (request.query_params.get('resource_id') or '').strip() or None
        bucket = (request.query_params.get('bucket') or '').strip().lower() or None
        if bucket and bucket not in ('day', 'week', 'month'):
            bucket = None

        data = PaymentAnalyticsService().get_summary(
            teacher_id=teacher_id,
            from_dt=from_dt,
            to_dt=to_dt,
            status=status_filter,
            resource_id=resource_id,
            bucket=bucket,
        )
        return Response(
            PaymentAnalyticsResponseSerializer(data).data,
            status=status.HTTP_200_OK,
        )
