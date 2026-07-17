import json

from rest_framework import serializers


class ExamAuditLogEntrySerializer(serializers.Serializer):
    uid = serializers.UUIDField(source="uid", read_only=True)
    event_type = serializers.CharField()
    event_data = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    student_id = serializers.UUIDField(read_only=True)

    def get_event_data(self, obj):
        raw = getattr(obj, "event_data", "{}") or "{}"
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}


def serialize_audit_log_entry(log):
    raw = getattr(log, "event_data", "{}") or "{}"
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        data = {}
    return {
        "uid": str(log.uid),
        "student_id": str(log.student_id),
        "event_type": log.event_type,
        "event_data": data,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def summarize_audit_logs(logs):
    """Trả về tổng hợp số lượng event theo loại."""
    by_type: dict[str, int] = {}
    for log in logs or []:
        by_type[log.event_type] = by_type.get(log.event_type, 0) + 1
    return {
        "all_events": len(logs or []),
        "by_type": by_type,
    }
