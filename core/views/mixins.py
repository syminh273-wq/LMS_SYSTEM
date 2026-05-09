from rest_framework.permissions import IsAuthenticated, IsAdminUser
from core.backend.auth.jwt_auth import CassandraJWTAuthentication


class JWTProtectedMixin:
    authentication_classes = [CassandraJWTAuthentication]
    permission_classes     = [IsAuthenticated]


class UserScopeMixin(JWTProtectedMixin):
    """Cho các endpoint yêu cầu user đã đăng nhập."""
    pass


class AdminScopeMixin(JWTProtectedMixin):
    """Cho các endpoint chỉ admin mới được truy cập."""
    permission_classes = [IsAuthenticated, IsAdminUser]
