from core.utils.uuid import uuid7
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class Exam(BaseTimeStampModel):
    uid = columns.UUID(
        primary_key=True,
        default=uuid7,
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

    is_online_active = columns.Boolean(default=False)
    opened_at = columns.DateTime(required=False)
    late_threshold_seconds = columns.Integer(default=0)

    # max_visibility_breaks: gộp tất cả (tab leave, window blur, app blur, fullscreen exit, visibility hidden)
    # max_face_warnings: cảnh báo camera/face (camera_lost, face_not_recognized, multiple_faces)
    # = 0 nghĩa là không giới hạn
    max_visibility_breaks = columns.Integer(default=3)
    max_face_warnings = columns.Integer(default=0)

    deleted_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'course_exams'
