from django.urls import include, path
from rest_framework.routers import DefaultRouter

from dummy.viewsets import DummyViewSet

router = DefaultRouter()
router.register(r'dummies', DummyViewSet, basename='dummy')

urlpatterns = [
    path('', include(router.urls)),
]
