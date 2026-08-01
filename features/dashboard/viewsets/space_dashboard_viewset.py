from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.dashboard.serializers.dashboard_serializers import (
    DashboardSummaryResponseSerializer,
)
from features.dashboard.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)


class SpaceDashboardViewSet(ViewSet):
    """GET /api/v1/space/dashboard/summary/"""

    permission_classes = [IsAuthenticated]
    service_class = DashboardService

    @property
    def service(self) -> DashboardService:
        if not hasattr(self, '_service'):
            self._service = self.service_class()
        return self._service


    def summary(self, request):
        try:
            data = self.service.get_summary(request.user.uid)
        except Exception as exc:
            logger.exception('[dashboard] summary failed: %s', exc)
            return Response(
                {'detail': 'Failed to build dashboard summary.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(DashboardSummaryResponseSerializer(data).data)
