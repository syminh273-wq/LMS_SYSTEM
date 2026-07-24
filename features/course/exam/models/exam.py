from django.utils.functional import cached_property
from core.utils.uuid import uuid7
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class Exam(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)

    uid = columns.UUID(
        primary_key=True,
        default=uuid7,
        clustering_order="DESC"
    )

    classroom_id = columns.UUID(index=True, required=True)

    teacher_id = columns.UUID(index=True, required=True)

    title = columns.Text(required=True)

    description = columns.Text(default='')

    content_type = columns.Text(required=True)  # discriminator: markdown|quiz|file|pdf|image

    body = columns.Text(default='')             # inline content (markdown text)

    ref_id = columns.UUID(required=False)       # generic FK: quiz_id OR resource_uid

    meta = columns.Text(default='{}')           # JSON: {url, name, size, ...}

    status = columns.Text(default='draft')

    is_deleted = columns.Boolean(default=False)

    due_date = columns.DateTime(required=False)

    exam_type = columns.Text(default='assignment')  # 'assignment' | 'quiz'
    exam_period = columns.Text(default='regular', index=True)  # 'regular' | 'midterm' | 'final'
    max_grade = columns.Float(default=10.0)
    camera_required = columns.Boolean(default=False)
    exam_mode = columns.Text(default='offline')
    duration_seconds = columns.Integer(default=0)

    # Online session tracking
    is_online_active = columns.Boolean(default=False)
    opened_at = columns.DateTime(required=False)
    late_threshold_seconds = columns.Integer(default=0)

    # Anti-cheat limits
    # max_visibility_breaks: gộp tất cả (tab leave, window blur, app blur, fullscreen exit, visibility hidden)
    # max_face_warnings: cảnh báo camera/face (camera_lost, face_not_recognized, multiple_faces)
    # = 0 nghĩa là không giới hạn
    max_visibility_breaks = columns.Integer(default=3)
    max_face_warnings = columns.Integer(default=0)

    deleted_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = 'uid'

    @cached_property
    def resolve_link(self):
        from features.sharing.repositories.link_repository import LinkRepository
        from features.sharing.serializers.link_response_serializer import LinkResponseSerializer
        from features.sharing.enums.resource_type import ResourceType

        repo = LinkRepository()
        link = repo.get_by_resource(
            resource_type=ResourceType.EXAM.value,
            resource_id=self.uid
        ).first()

        if link:
            return LinkResponseSerializer(link).data
        return None

    __table_name__ = 'course_exams'