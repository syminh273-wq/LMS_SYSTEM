from rest_framework import serializers


class CourseLessonResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    course_uid = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    video_url = serializers.SerializerMethodField()
    material_urls = serializers.SerializerMethodField()
    order_index = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()
    is_preview = serializers.BooleanField()
    is_published = serializers.BooleanField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_video_url(self, obj):
        rid = getattr(obj, 'video_resource_uid', None)
        if not rid:
            return None
        return _resolve_resource_url(rid)

    def get_material_urls(self, obj):
        rids = getattr(obj, 'material_resource_uids', None) or []
        out = []
        for rid in rids:
            data = _resolve_resource_full(rid)
            if data:
                out.append(data)
        return out


class CourseResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    pid = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    cover_url = serializers.CharField()
    teacher_id = serializers.UUIDField(read_only=True)
    pricing_type = serializers.CharField()
    price_vnd = serializers.IntegerField()
    status = serializers.CharField()
    classroom_uid = serializers.UUIDField(read_only=True)
    resolve_link = serializers.DictField(read_only=True)
    lesson_count = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_lesson_count(self, obj):
        from features.course.repositories import CourseLessonRepository
        return CourseLessonRepository().get_by_course(obj.uid).count()

    def get_enrollment_count(self, obj):
        from features.course.repositories import CourseEnrollmentRepository
        return CourseEnrollmentRepository().count_for_course(obj.uid)


class CourseEnrollmentResponseSerializer(serializers.Serializer):
    consumer_id = serializers.UUIDField()
    consumer_name = serializers.CharField()
    consumer_avatar = serializers.CharField()
    enrolled_at = serializers.DateTimeField()
    pricing_type = serializers.CharField()
    amount_vnd = serializers.IntegerField()
    payment_order_id = serializers.CharField(allow_null=True)


class CoursePreviewLessonSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    order_index = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()
    video_url = serializers.SerializerMethodField()
    material_urls = serializers.SerializerMethodField()

    def get_video_url(self, obj):
        rid = getattr(obj, 'video_resource_uid', None)
        if not rid:
            return None
        return _resolve_resource_url(rid)

    def get_material_urls(self, obj):
        rids = getattr(obj, 'material_resource_uids', None) or []
        out = []
        for rid in rids:
            data = _resolve_resource_full(rid)
            if data:
                out.append(data)
        return out


class CoursePreviewSerializer(serializers.Serializer):
    course = serializers.SerializerMethodField()
    is_free = serializers.BooleanField()
    requires_payment = serializers.BooleanField()
    preview_lessons = CoursePreviewLessonSerializer(many=True)

    def get_course(self, obj):
        c = obj['course']
        return {
            'uid': str(c.uid),
            'pid': c.pid,
            'name': c.name,
            'description': c.description or '',
            'cover_url': c.cover_url or '',
            'teacher_id': str(c.teacher_id),
            'pricing_type': c.pricing_type,
            'price_vnd': int(c.price_vnd or 0),
            'status': c.status,
        }


def _resolve_resource_url(resource_uid):
    try:
        from features.resource.models import Resource
        r = Resource.objects.filter(uid=resource_uid, is_deleted=False).first()
        if r:
            return r.url
    except Exception:
        pass
    return None


def _resolve_resource_full(resource_uid):
    try:
        from features.resource.models import Resource
        r = Resource.objects.filter(uid=resource_uid, is_deleted=False).first()
        if r:
            return {
                'uid': str(r.uid),
                'name': r.name,
                'url': r.url,
                'file_type': r.file_type,
            }
    except Exception:
        pass
    return None
