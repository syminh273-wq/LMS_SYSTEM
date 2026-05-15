from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.space.viewsets import ViewSet
from features.account.space.views.space_register_view import SpaceRegisterView
from features.account.space.views.space_login_view import SpaceLoginView

router = DefaultRouter(trailing_slash=True)
router.register(r'spaces', ViewSet, basename='api_spaces')

urlpatterns = [
    path('register/', SpaceRegisterView.as_view(), name='space_register'),
    path('login/', SpaceLoginView.as_view(), name='space_login'),
    path('', include(router.urls)),
]
