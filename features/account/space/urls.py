from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.space.viewsets import ViewSet
from features.account.space.views.space_register_view import SpaceRegisterView
from features.account.space.views.space_login_view import SpaceLoginView
from features.account.space.views.google_oauth_view import (
    GoogleSpaceOAuthLoginView,
    GoogleSpaceOAuthCallbackView,
)

router = DefaultRouter(trailing_slash=True)
router.register(r'spaces', ViewSet, basename='api_spaces')

urlpatterns = [
    path('register/', SpaceRegisterView.as_view(), name='space_register'),
    path('login/', SpaceLoginView.as_view(), name='space_login'),
    path('auth/google/login/', GoogleSpaceOAuthLoginView.as_view(), name='space_google_login'),
    path('auth/google/callback/', GoogleSpaceOAuthCallbackView.as_view(), name='space_google_callback'),
    path('', include(router.urls)),
]
