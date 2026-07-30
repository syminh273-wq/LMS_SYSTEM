from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.dashboard.viewsets.consumer_dashboard_viewset import ConsumerDashboardViewSet

router = DefaultRouter()
router.register(r'', ConsumerDashboardViewSet, basename='consumer-dashboard')

_dashboard = ConsumerDashboardViewSet.as_view({
    'get': 'summary',
})

urlpatterns = [
    path('summary/', _dashboard, name='consumer-dashboard-summary'),
    path('', include(router.urls)),
]
