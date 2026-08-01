from rest_framework import serializers
from core.utils.datetime import to_vn, to_vn_iso


class VnDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return to_vn_iso(value)

    def to_internal_value(self, value):
        dt = super().to_internal_value(value)
        return to_vn(dt)
