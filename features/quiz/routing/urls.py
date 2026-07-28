from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.quiz.viewsets.quiz_viewset import QuizViewSet

router = DefaultRouter()
router.register(r'', QuizViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
]
