from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.consumer.viewsets import ConsumerViewSet
from features.account.consumer.views.consumer_search_view import ConsumerSearchAPIView
from features.account.consumer.views.consumer_update_view import ConsumerUpdateView
from features.account.consumer.views.student_profile_views import StudentProfileSettingsView

router = DefaultRouter(trailing_slash=True)
router.register(r'consumers', ConsumerViewSet, basename='api_consumers')

urlpatterns = [
    path('', include(router.urls)),
    path('update-profile/', ConsumerUpdateView.as_view(), name='api_update_profile'),
    path('profile-settings/', StudentProfileSettingsView.as_view(), name='profile-settings'),
    path('search/', ConsumerSearchAPIView.as_view(), name='consumer-search'),
]
