from django.urls import path
from features.history.viewsets.consumer_history_viewset import ConsumerHistoryViewSet

urlpatterns = [
    path('', ConsumerHistoryViewSet.as_view({'get': 'list'}), name='consumer-history'),
]
