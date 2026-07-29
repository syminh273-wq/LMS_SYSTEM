from django.urls import path
from features.account.consumer.views.consumer_login_view import ConsumerLoginView
from features.account.consumer.views.consumer_register_view import ConsumerRegisterView
from features.account.consumer.views.consumer_token_refresh_view import ConsumerAccountTokenRefreshView
from features.account.consumer.views.google_oauth_view import (
    GoogleConsumerOAuthLoginView,
    GoogleConsumerOAuthCallbackView,
)
from features.account.consumer.views.consumer_forgot_password_view import ConsumerForgotPasswordView
from features.account.consumer.views.consumer_verify_otp_view import ConsumerVerifyOTPView
from features.account.consumer.views.consumer_reset_password_view import ConsumerResetPasswordView
from features.account.consumer.views.consumer_pid_view import ConsumerByPidView
from features.account.consumer.views.student_profile_views import PublicStudentProfileView

urlpatterns = [
    path('login/', ConsumerLoginView.as_view(), name='api_login'),
    path('register/', ConsumerRegisterView.as_view(), name='api_register'),
    path('token/refresh/', ConsumerAccountTokenRefreshView.as_view(), name='consumer_token_refresh'),
    path('auth/google/login/', GoogleConsumerOAuthLoginView.as_view(), name='consumer_google_login'),
    path('auth/google/callback/', GoogleConsumerOAuthCallbackView.as_view(), name='consumer_google_callback'),
    path('forgot-password/', ConsumerForgotPasswordView.as_view(), name='consumer-forgot-password'),
    path('verify-otp/', ConsumerVerifyOTPView.as_view(), name='consumer-verify-otp'),
    path('reset-password/', ConsumerResetPasswordView.as_view(), name='consumer-reset-password'),
    path('profile/<str:consumer_uid>/public/', PublicStudentProfileView.as_view(), name='profile-public'),
    path('by-pid/<str:pid>/', ConsumerByPidView.as_view(), name='consumer-by-pid'),
]
