from rest_framework import serializers
from ..constants import VoiceNames

class UserSettingSerializer(serializers.Serializer):
    """Generic key-value setting serializer."""
    key = serializers.CharField()
    value = serializers.CharField()

class UserBulkSettingsSerializer(serializers.Serializer):
    """Serializer for multiple settings (dictionary input)."""
    settings = serializers.JSONField()

class AvailableVoiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()

class PreviewVoiceRequestSerializer(serializers.Serializer):
    voice_name = serializers.ChoiceField(choices=VoiceNames.CHOICES)
    text = serializers.CharField(max_length=200, required=False, default="Đây là bản nghe thử giọng nói.")
