from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.quiz_collection.viewsets.space_quiz_collection_viewset import SpaceQuizCollectionViewSet
from features.quiz_collection.viewsets.space_certificate_viewset import SpaceCertificateViewSet

router = DefaultRouter()
router.register(r'', SpaceQuizCollectionViewSet, basename='quiz-collection')

certificate_router = DefaultRouter()
certificate_router.register(r'', SpaceCertificateViewSet, basename='certificate')

urlpatterns = [
    path('quiz-collection/', include(router.urls)),
    path('certificate/', include(certificate_router.urls)),
]
