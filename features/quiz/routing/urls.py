from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.quiz.viewsets.space_quiz_viewset import SpaceQuizViewSet

router = DefaultRouter()
router.register(r'', SpaceQuizViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
]
