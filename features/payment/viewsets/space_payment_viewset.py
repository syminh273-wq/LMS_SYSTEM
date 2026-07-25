from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.payment.serializers.payment_analytics_serializer import (
    PaymentAnalyticsResponseSerializer,
)
from features.payment.services.payment_analytics_service import (
    PaymentAnalyticsService,
    default_window,
    parse_date_param,
)


class SpacePaymentViewSet(ViewSet):
    """Teacher-side payment received view (history of payments for classrooms they own)."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET /api/v1/space/payment/
        Query params: ?status=completed&limit=50
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
        """GET /api/v1/space/payment/summary/

        Query params:
            from  (ISO date, optional)
            to    (ISO date, optional)
            status (completed|pending|failed|cancelled)
            resource_id (classroom uid)
            bucket (day|week|month) — auto when omitted
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
