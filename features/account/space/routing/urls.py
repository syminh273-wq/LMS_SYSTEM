from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.space.viewsets import ViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r'spaces', ViewSet, basename='api_spaces')

urlpatterns = [
    path('mine/', ViewSet.as_view({'get': 'mine', 'patch': 'mine'}), name='space_account_mine'),
    path('settings/', ViewSet.as_view({'get': 'get_settings', 'patch': 'update_settings'}), name='space_account_settings'),
    path('change-password/', ViewSet.as_view({'post': 'change_password'}), name='space_change_password'),
    path('', include(router.urls)),
]
