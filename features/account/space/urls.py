from django.urls import include, path
from rest_framework.routers import DefaultRouter
from features.account.space.viewsets import ViewSet
from features.account.space.views.space_register_view import SpaceRegisterView
from features.account.space.views.space_login_view import SpaceLoginView
from features.account.space.views.google_oauth_view import (
    GoogleSpaceOAuthLoginView,
    GoogleSpaceOAuthCallbackView,
)
from features.account.consumer.views.teacher_settings_view import TeacherSettingsView
from features.account.space.views.space_forgot_password_view import SpaceForgotPasswordView
from features.account.space.views.space_verify_otp_view import SpaceVerifyOTPView
from features.account.space.views.space_reset_password_view import SpaceResetPasswordView

router = DefaultRouter(trailing_slash=True)
router.register(r'spaces', ViewSet, basename='api_spaces')

urlpatterns = [
    path('mine/', ViewSet.as_view({'get': 'mine', 'patch': 'mine'}), name='space_account_mine'),
    path('change-password/', ViewSet.as_view({'post': 'change_password'}), name='space_change_password'),
    path('register/', SpaceRegisterView.as_view(), name='space_register'),
    path('login/', SpaceLoginView.as_view(), name='space_login'),
    path('auth/google/login/', GoogleSpaceOAuthLoginView.as_view(), name='space_google_login'),
    path('auth/google/callback/', GoogleSpaceOAuthCallbackView.as_view(), name='space_google_callback'),
    path('settings/', TeacherSettingsView.as_view(), name='teacher_settings'),
    path('forgot-password/', SpaceForgotPasswordView.as_view(), name='space-forgot-password'),
    path('verify-otp/', SpaceVerifyOTPView.as_view(), name='space-verify-otp'),
    path('reset-password/', SpaceResetPasswordView.as_view(), name='space-reset-password'),
    path('', include(router.urls)),
]
