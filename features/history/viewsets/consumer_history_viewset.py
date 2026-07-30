from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import ConsumerScopeMixin
from features.history.services.history_service import HistoryService
from features.payment.serializers.payment_response_serializer import PaymentResponseSerializer


class ConsumerHistoryViewSet(ConsumerScopeMixin, ViewSet):
    """Payment history for the current student. Classroom joins are derived
    client-side from completed classroom payments."""

    def list(self, request):
        """GET /api/v1/consumer/history/
        Query params: ?limit=50
        @return: { payments: [...] }
        """
        try:
            limit = int(request.query_params.get('limit') or 50)
        except (TypeError, ValueError):
            limit = 50

        overview = HistoryService().get_overview(request.user.uid, limit=limit)
        payments_data = PaymentResponseSerializer(overview['payments'], many=True).data

        return Response({'payments': payments_data})
