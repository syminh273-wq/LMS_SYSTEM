from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.resource.viewsets.resource_viewset import ResourceViewSet

router = DefaultRouter()
router.register(r'', ResourceViewSet, basename='resource')

urlpatterns = [
    path('', include(router.urls)),
]
