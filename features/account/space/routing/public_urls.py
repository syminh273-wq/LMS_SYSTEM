from django.urls import path
from features.account.space.views.space_register_view import SpaceRegisterView
from features.account.space.views.space_login_view import SpaceLoginView
from features.account.space.views.space_token_refresh_view import SpaceAccountTokenRefreshView
from features.account.space.views.google_oauth_view import (
    GoogleSpaceOAuthLoginView,
    GoogleSpaceOAuthCallbackView,
)
from features.account.space.views.space_forgot_password_view import SpaceForgotPasswordView
from features.account.space.views.space_verify_otp_view import SpaceVerifyOTPView
from features.account.space.views.space_reset_password_view import SpaceResetPasswordView

urlpatterns = [
    path('register/', SpaceRegisterView.as_view(), name='space_register'),
    path('login/', SpaceLoginView.as_view(), name='space_login'),
    path('token/refresh/', SpaceAccountTokenRefreshView.as_view(), name='space_token_refresh'),
    path('auth/google/login/', GoogleSpaceOAuthLoginView.as_view(), name='space_google_login'),
    path('auth/google/callback/', GoogleSpaceOAuthCallbackView.as_view(), name='space_google_callback'),
    path('forgot-password/', SpaceForgotPasswordView.as_view(), name='space-forgot-password'),
    path('verify-otp/', SpaceVerifyOTPView.as_view(), name='space-verify-otp'),
    path('reset-password/', SpaceResetPasswordView.as_view(), name='space-reset-password'),
]
