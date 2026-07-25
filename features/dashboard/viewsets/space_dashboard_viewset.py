"""Space (teacher) dashboard endpoints.

Provides aggregate KPIs, weekly trend, top classes and recent activity
in a single round-trip so the dashboard can render without N+1 calls.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.dashboard.serializers.dashboard_serializers import (
    DashboardSummaryResponseSerializer,
    DashboardUsageResponseSerializer,
)
from features.dashboard.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)


class SpaceDashboardViewSet(ViewSet):
    """GET /api/v1/space/dashboard/summary/
    GET /api/v1/space/dashboard/usage/
    """

    permission_classes = [IsAuthenticated]
    service_class = DashboardService

    @property
    def service(self) -> DashboardService:
        if not hasattr(self, '_service'):
            self._service = self.service_class()
        return self._service

    def list(self, request):
        """Default action — alias for summary."""
        return self.summary(request)

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

    def usage(self, request):
        try:
            data = self.service.get_usage(request.user.uid)
        except Exception as exc:
            logger.exception('[dashboard] usage failed: %s', exc)
            return Response(
                {'detail': 'Failed to build dashboard usage.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(DashboardUsageResponseSerializer(data).data)
