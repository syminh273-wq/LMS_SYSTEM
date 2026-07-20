from rest_framework import serializers

from features.course.classroom.repositories.classroom_repository import Repository as ClassroomRepository


class CalendarEventSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    classroom_id = serializers.UUIDField(required=False, allow_null=True)
    classroom_name = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    space_id = serializers.UUIDField(read_only=True)
    owner_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_classroom_name(self, obj):
        cid = getattr(obj, 'classroom_id', None)
        if not cid:
            return None
        cache = self.context.get('classroom_name_cache') if self.context else None
        if cache is not None:
            if str(cid) in cache:
                return cache[str(cid)]
        try:
            classroom = ClassroomRepository().find(cid)
            if cache is not None:
                cache[str(cid)] = classroom.name
            return classroom.name
        except Exception:
            return None

    def get_color(self, obj):
        type_ = getattr(obj, 'type', None)
        return TYPE_COLORS.get(type_, 'slate')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('start_time'):
            data['start_time'] = _isoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = _isoformat(data['end_time'])
        if data.get('created_at'):
            data['created_at'] = _isoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = _isoformat(data['updated_at'])
        return data


class CalendarEventCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['class', 'exam', 'deadline', 'study_session'])
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    classroom_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs['end_time'] <= attrs['start_time']:
            raise serializers.ValidationError({'end_time': 'Thời gian kết thúc phải sau thời gian bắt đầu.'})
        return attrs


class RecurringSlotSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()


class RecurringScheduleCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=['class', 'exam', 'deadline', 'study_session'], default='class')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    classroom_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    slots = RecurringSlotSerializer(many=True)

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.'})
        if not attrs.get('slots'):
            raise serializers.ValidationError({'slots': 'Vui lòng cung cấp ít nhất 1 slot thời gian.'})
        for slot in attrs['slots']:
            if slot['end_time'] <= slot['start_time']:
                raise serializers.ValidationError({'slots': 'Mỗi slot phải có end_time > start_time.'})
        return attrs


TYPE_COLORS = {
    'class': 'indigo',
    'exam': 'rose',
    'deadline': 'amber',
    'study_session': 'emerald',
}


def _isoformat(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value
