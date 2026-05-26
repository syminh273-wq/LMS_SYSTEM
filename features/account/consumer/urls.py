from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.consumer.viewsets.consumer_viewset import ViewSet
from features.account.consumer.views.consumer_login_view import ConsumerLoginView
from features.account.consumer.views.consumer_register_view import ConsumerRegisterView
from features.account.consumer.views.consumer_update_view import ConsumerUpdateView
from features.account.consumer.views.google_oauth_view import (
    GoogleConsumerOAuthLoginView,
    GoogleConsumerOAuthCallbackView,
)

router = DefaultRouter(trailing_slash=True)
router.register(r'consumers', ViewSet, basename='api_consumers')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', ConsumerLoginView.as_view(), name='api_login'),
    path('register/', ConsumerRegisterView.as_view(), name='api_register'),
    path('update-profile/', ConsumerUpdateView.as_view(), name='api_update_profile'),
    path('auth/google/login/', GoogleConsumerOAuthLoginView.as_view(), name='consumer_google_login'),
    path('auth/google/callback/', GoogleConsumerOAuthCallbackView.as_view(), name='consumer_google_callback'),
]
