from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class CourseLesson(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    course_uid = columns.UUID(primary_key=True, clustering_order="ASC")
    order_index = columns.Integer(primary_key=True, default=0, clustering_order="ASC")
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="ASC")
    title = columns.Text(required=True)
    description = columns.Text(default='')
    video_resource_uid = columns.UUID(required=False)
    material_resource_uids = columns.List(columns.UUID)
    duration_seconds = columns.Integer(default=0)
    is_preview = columns.Boolean(default=False)
    is_published = columns.Boolean(default=True)

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'course_lessons'
