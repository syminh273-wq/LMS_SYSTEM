from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets.voice_setting_viewset import UserVoiceSettingViewSet

router = DefaultRouter()
router.register(r'', UserVoiceSettingViewSet, basename='voice-setting')

urlpatterns = [
    path('', UserVoiceSettingViewSet.as_view({'get': 'list', 'patch': 'patch'}), name='voice-setting-root'),
    path('', include(router.urls)),
]
