from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.space.viewsets import ViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'spaces', ViewSet, basename='api_spaces')

urlpatterns = [
    path('', include(router.urls)),
]
