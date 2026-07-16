from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.quiz_collection.viewsets.certificate_viewset import CertificateViewSet

router = DefaultRouter()
router.register(r'', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('', include(router.urls)),
]
