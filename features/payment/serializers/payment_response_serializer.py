from core.serializers.fields import VnDateTimeField

from rest_framework import serializers

from features.payment.utils import parse_meta


class PaymentResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    consumer_id = serializers.UUIDField(read_only=True)
    teacher_id = serializers.UUIDField(read_only=True, required=False, allow_null=True)
    order_id = serializers.CharField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    order_info = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    pay_url = serializers.CharField(read_only=True)
    result_code = serializers.IntegerField(read_only=True)
    trans_id = serializers.IntegerField(read_only=True)
    created_at = VnDateTimeField(read_only=True)
    updated_at = VnDateTimeField(read_only=True)
    resource_type = serializers.SerializerMethodField()
    resource_id = serializers.SerializerMethodField()
    resource_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()

    def to_representation(self, instance):
        self._meta = parse_meta(getattr(instance, 'extra_data', ''))
        return super().to_representation(instance)

    def get_resource_type(self, obj):
        return self._meta.get('resource_type')

    def get_resource_id(self, obj):
        return self._meta.get('resource_id')

    def get_resource_name(self, obj):
        if not self.context.get('with_details'):
            return None
        resource_type = self._meta.get('resource_type')
        resource_id = self._meta.get('resource_id')
        if not resource_type or not resource_id:
            return None
        try:
            if resource_type == 'classroom':
                from features.course.classroom.repositories import Repository as ClassroomRepository
                classroom = ClassroomRepository().find(resource_id)
                return getattr(classroom, 'name', None)
            if resource_type == 'course':
                from features.course.repositories import CourseRepository
                course = CourseRepository().find(resource_id)
                return getattr(course, 'name', None)
        except Exception:
            return None
        return None

    def get_teacher_name(self, obj):
        if not self.context.get('with_details'):
            return None
        teacher_id = getattr(obj, 'teacher_id', None)
        if not teacher_id:
            return None
        try:
            from features.account.space.repositories import Repository as SpaceRepository
            teacher = SpaceRepository().find(str(teacher_id))
            return getattr(teacher, 'full_name', None) or getattr(teacher, 'name', None)
        except Exception:
            return None


class PaymentInitiateResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    pay_url = serializers.CharField()
    deeplink = serializers.CharField()
    qr_code_url = serializers.CharField()
    status = serializers.CharField(required=False, allow_blank=True)
