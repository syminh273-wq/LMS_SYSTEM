import io
import uuid
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from features.account.space.models.space import Space
from core.ai.tts.edge_tts_client import TTSClient
from core.storages.storage_service import storage_service
from ..services.user_setting_service import UserSettingService
from ..serializers.user_setting_serializer import (
    UserSettingSerializer,
    UserBulkSettingsSerializer,
    AvailableVoiceSerializer,
    PreviewVoiceRequestSerializer
)
from ..constants import VoiceNames, UserTypes

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

    def patch(self, request):
        """Partial update of settings"""
        return self.create(request)

    @action(detail=False, methods=['get'], url_path='available-voices')
    def available_voices(self, request):
        """Get list of available voices"""
        voices = [{"id": choice[0], "name": choice[1]} for choice in VoiceNames.CHOICES]
        serializer = AvailableVoiceSerializer(voices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='preview')
    def preview(self, request):
        """Generate a preview audio for a voice"""
        serializer = PreviewVoiceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        voice_name = serializer.validated_data['voice_name']
        text = serializer.validated_data['text']
        
        try:
            audio_bytes = TTSClient.synthesize(text, voice=voice_name)
            if not audio_bytes:
                return Response({"error": "Failed to synthesize audio"}, status=status.HTTP_400_BAD_REQUEST)
                
            file_name = f"previews/voice_{voice_name}_{uuid.uuid4().hex[:8]}.mp3"
            upload_result = storage_service.upload_fileobj(
                io.BytesIO(audio_bytes),
                file_name,
                is_public=True
            )
            
            if not upload_result.get('success'):
                return Response({"error": upload_result.get('message')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            return Response({
                "url": upload_result.get('url'),
                "voice_name": voice_name,
                "text": text
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
