from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.quiz.viewsets.consumer_quiz_viewset import ConsumerQuizViewSet

router = DefaultRouter()
router.register(r'', ConsumerQuizViewSet, basename='consumer-quiz')

urlpatterns = [
    path('', include(router.urls)),
]
