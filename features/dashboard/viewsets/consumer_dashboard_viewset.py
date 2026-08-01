from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import ConsumerScopeMixin
from features.dashboard.serializers.consumer_dashboard_serializers import (
    ConsumerDashboardSummaryResponseSerializer,
)
from features.dashboard.services.consumer_dashboard_service import ConsumerDashboardService

logger = logging.getLogger(__name__)


class ConsumerDashboardViewSet(ConsumerScopeMixin, ViewSet):
    """GET /api/v1/consumer/dashboard/summary/"""

    service_class = ConsumerDashboardService

    @property
    def service(self) -> ConsumerDashboardService:
        if not hasattr(self, '_service'):
            self._service = self.service_class()
        return self._service

    def summary(self, request):
        try:
            data = self.service.get_summary(request.user.uid)
        except Exception as exc:
            logger.exception('[dashboard] consumer summary failed: %s', exc)
            return Response(
                {'detail': 'Failed to build dashboard summary.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(ConsumerDashboardSummaryResponseSerializer(data).data)
