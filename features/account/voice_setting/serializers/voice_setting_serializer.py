from rest_framework import serializers
from ..constants import VoiceNames

class UserVoiceSettingSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(read_only=True)
    user_type = serializers.CharField(read_only=True)
    voice_name = serializers.ChoiceField(choices=VoiceNames.CHOICES, default=VoiceNames.VI_HOAI_MY)
    is_voice_enabled = serializers.BooleanField(default=True)
    language = serializers.CharField(max_length=10, default='vi-VN')
    updated_at = serializers.DateTimeField(read_only=True)

class AvailableVoiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()

class PreviewVoiceRequestSerializer(serializers.Serializer):
    voice_name = serializers.ChoiceField(choices=VoiceNames.CHOICES)
    text = serializers.CharField(max_length=200, required=False, default="Đây là bản nghe thử giọng nói.")
