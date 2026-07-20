from rest_framework import serializers


def _isoformat(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


class LeaveRequestSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    student_id = serializers.UUIDField()
    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    space_id = serializers.UUIDField()
    classroom_id = serializers.SerializerMethodField()
    classroom_name = serializers.SerializerMethodField()
    event_id = serializers.UUIDField(required=False, allow_null=True)
    event_title = serializers.SerializerMethodField()
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField()
    evidence_url = serializers.CharField(read_only=True)
    status = serializers.CharField()
    processed_by = serializers.UUIDField(read_only=True)
    processed_at = serializers.DateTimeField(read_only=True)
    rejection_reason = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def _student_cache(self):
        if self.context is None:
            self.context = {}
        if 'student_cache' not in self.context:
            self.context['student_cache'] = {}
        return self.context['student_cache']

    def _event_cache(self):
        if self.context is None:
            self.context = {}
        if 'event_cache' not in self.context:
            self.context['event_cache'] = {}
        return self.context['event_cache']

    def _classroom_cache(self):
        if self.context is None:
            self.context = {}
        if 'classroom_name_cache' not in self.context:
            self.context['classroom_name_cache'] = {}
        return self.context['classroom_name_cache']

    def _get_event(self, event_id):
        cache = self._event_cache()
        key = str(event_id)
        if key in cache:
            return cache[key]
        try:
            from features.calendar.services.calendar_service import CalendarService
            event = CalendarService().find(key)
        except Exception:
            return None
        info = {
            'title': event.title,
            'classroom_id': str(event.classroom_id) if getattr(event, 'classroom_id', None) else None,
        }
        cache[key] = info
        return info

    def get_student_name(self, obj):
        if not getattr(obj, 'student_id', None):
            return None
        cache = self._student_cache()
        key = str(obj.student_id)
        if key in cache:
            return cache[key].get('name')
        try:
            from features.account.consumer.repositories.consumer_repository import ConsumerRepository
            consumer = ConsumerRepository().find(key)
            cache[key] = {'name': consumer.full_name or consumer.username, 'email': consumer.email}
            return cache[key]['name']
        except Exception:
            return None

    def get_student_email(self, obj):
        if not getattr(obj, 'student_id', None):
            return None
        cache = self._student_cache()
        key = str(obj.student_id)
        if key in cache:
            return cache[key].get('email')
        try:
            from features.account.consumer.repositories.consumer_repository import ConsumerRepository
            consumer = ConsumerRepository().find(key)
            cache[key] = {'name': consumer.full_name or consumer.username, 'email': consumer.email}
            return cache[key]['email']
        except Exception:
            return None

    def get_event_title(self, obj):
        if not getattr(obj, 'event_id', None):
            return None
        info = self._get_event(obj.event_id)
        return info.get('title') if info else None

    def get_classroom_id(self, obj):
        direct = getattr(obj, 'classroom_id', None)
        if direct:
            return str(direct)
        if not getattr(obj, 'event_id', None):
            return None
        info = self._get_event(obj.event_id)
        return info.get('classroom_id') if info else None

    def get_classroom_name(self, obj):
        classroom_id = self.get_classroom_id(obj)
        if not classroom_id:
            return None
        cache = self._classroom_cache()
        if classroom_id in cache:
            return cache[classroom_id]
        try:
            from features.course.classroom.repositories.classroom_repository import Repository as ClassroomRepository
            classroom = ClassroomRepository().find(classroom_id)
            cache[classroom_id] = classroom.name
            return classroom.name
        except Exception:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ('start_date', 'end_date', 'processed_at', 'created_at', 'updated_at'):
            if data.get(key):
                data[key] = _isoformat(data[key])
        return data


class LeaveRequestCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField(required=False, allow_null=True)
    classroom_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=2000)
    evidence_file = serializers.FileField(required=False, allow_null=True, write_only=True)

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and end <= start:
            raise serializers.ValidationError({'end_date': 'Thời gian kết thúc phải sau thời gian bắt đầu.'})
        if not attrs.get('event_id') and not (start and end):
            raise serializers.ValidationError({'non_field_errors': 'Cần chọn sự kiện hoặc khoảng thời gian.'})
        return attrs


class LeaveRequestProcessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate(self, attrs):
        if attrs['status'] == 'rejected' and not attrs.get('rejection_reason', '').strip():
            raise serializers.ValidationError({'rejection_reason': 'Vui lòng nhập lý do từ chối.'})
        return attrs
