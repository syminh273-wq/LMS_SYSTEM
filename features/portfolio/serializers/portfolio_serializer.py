import json
from rest_framework import serializers
from features.portfolio.models import Portfolio


class PortfolioEntrySerializer(serializers.Serializer):
    uid = serializers.UUIDField(required=False)
    key = serializers.ChoiceField(choices=Portfolio.VALID_KEYS)
    value = serializers.JSONField()
    is_public = serializers.BooleanField(required=False, default=True)
    display_order = serializers.IntegerField(required=False, default=0)

    def to_representation(self, instance):
        if isinstance(instance, dict) and 'value' in instance and isinstance(instance['value'], str):
            try:
                instance = dict(instance)
                instance['value'] = json.loads(instance['value'])
            except (TypeError, json.JSONDecodeError):
                pass
        return super().to_representation(instance)


class PortfolioBulkUpdateSerializer(serializers.Serializer):
    entries = PortfolioEntrySerializer(many=True)


class PortfolioReorderSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    display_order = serializers.IntegerField()


class PortfolioReorderBulkSerializer(serializers.Serializer):
    orders = PortfolioReorderSerializer(many=True)


class PortfolioUploadResponseSerializer(serializers.Serializer):
    file_key = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)
