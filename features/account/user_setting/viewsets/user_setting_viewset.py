from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from features.account.space.models.space import Space
from ..services.user_setting_service import UserSettingService
from ..enums import UserTypes

class UserSettingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    service = UserSettingService()

    def _get_user_type(self, user):
        return UserTypes.SPACE if isinstance(user, Space) else UserTypes.CONSUMER

    def list(self, request):
        """Get all current user settings"""
        settings = self.service.get_all_settings(request.user.uid)
        return Response(settings)

    def create(self, request):
        """Update/Create multiple settings at once"""
        user_type = self._get_user_type(request.user)
        
        # Flexibility: support both {"settings": {...}} and {...} directly
        settings_data = request.data.get('settings')
        if settings_data is None:
            # If "settings" key is missing, treat the whole body as settings
            settings_data = request.data

        if not isinstance(settings_data, dict):
            return Response(
                {"error": "Dữ liệu settings phải là một object (dictionary)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.service.update_bulk_settings(
            request.user.uid,
            user_type,
            settings_data
        )
        return Response(self.service.get_all_settings(request.user.uid))
