from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenViewBase

from core.backend.auth.refresh import AccountTokenRefreshSerializer


class ConsumerAccountTokenRefreshView(TokenViewBase):
    serializer_class = AccountTokenRefreshSerializer
    permission_classes = [AllowAny]
