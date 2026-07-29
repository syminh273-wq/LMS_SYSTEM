from rest_framework.permissions import BasePermission, IsAuthenticated, IsAdminUser
from core.backend.auth.jwt_auth import CassandraJWTAuthentication


class JWTProtectedMixin:
    authentication_classes = [CassandraJWTAuthentication]
    permission_classes     = [IsAuthenticated]


class UserScopeMixin(JWTProtectedMixin):
    """Cho các endpoint yêu cầu user đã đăng nhập (dùng chung cho cả Space và Consumer)."""
    pass


class IsSpaceUser(BasePermission):
    """request.user phải là tài khoản Space (giáo viên)."""

    def has_permission(self, request, view):
        from features.account.space.models.space import Space
        return isinstance(request.user, Space)


class IsConsumerUser(BasePermission):
    """request.user phải là tài khoản Consumer (học sinh)."""

    def has_permission(self, request, view):
        from features.account.consumer.models.consumer import Consumer
        return isinstance(request.user, Consumer)


class SpaceScopeMixin(JWTProtectedMixin):
    """Cho các endpoint chỉ Space (giáo viên) mới được truy cập."""
    permission_classes = [IsAuthenticated, IsSpaceUser]


class ConsumerScopeMixin(JWTProtectedMixin):
    """Cho các endpoint chỉ Consumer (học sinh) mới được truy cập."""
    permission_classes = [IsAuthenticated, IsConsumerUser]


class AdminScopeMixin(JWTProtectedMixin):
    """Cho các endpoint chỉ admin mới được truy cập."""
    permission_classes = [IsAuthenticated, IsAdminUser]
