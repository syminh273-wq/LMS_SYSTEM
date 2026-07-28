from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.quiz_collection.viewsets.consumer_quiz_collection_viewset import (
    ConsumerQuizCollectionViewSet,
)

router = DefaultRouter()
router.register(r'', ConsumerQuizCollectionViewSet, basename='consumer-quiz-collection')

urlpatterns = [
    path('', include(router.urls)),
]
