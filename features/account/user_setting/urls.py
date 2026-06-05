from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets.user_setting_viewset import UserSettingViewSet

router = DefaultRouter()
router.register(r'', UserSettingViewSet, basename='user-setting')

urlpatterns = [
    path('', include(router.urls)),
]
