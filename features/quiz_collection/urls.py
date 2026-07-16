from django.urls import path, include
from rest_framework.routers import DefaultRouter

from features.quiz_collection.viewsets.quiz_collection_viewset import QuizCollectionViewSet

router = DefaultRouter()
router.register(r'', QuizCollectionViewSet, basename='quiz-collection')

urlpatterns = [
    path('', include(router.urls)),
]
