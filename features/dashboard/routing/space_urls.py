from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.dashboard.viewsets.space_dashboard_viewset import SpaceDashboardViewSet

router = DefaultRouter()
router.register(r'', SpaceDashboardViewSet, basename='space-dashboard')

_dashboard = SpaceDashboardViewSet.as_view({
    'get': 'summary',
})

urlpatterns = [
    path('summary/', _dashboard, name='space-dashboard-summary'),
    path('', include(router.urls)),
]
