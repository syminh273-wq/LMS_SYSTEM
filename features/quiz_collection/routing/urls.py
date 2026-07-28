from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.quiz_collection.viewsets.quiz_collection_viewset import QuizCollectionViewSet
from features.quiz_collection.viewsets.certificate_viewset import CertificateViewSet

router = DefaultRouter()
router.register(r'', QuizCollectionViewSet, basename='quiz-collection')

certificate_router = DefaultRouter()
certificate_router.register(r'', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('quiz-collection/', include(router.urls)),
    path('certificate/', include(certificate_router.urls)),
]
