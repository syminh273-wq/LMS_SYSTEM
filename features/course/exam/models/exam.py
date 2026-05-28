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

    content_type = columns.Text(required=True)

    content = columns.Text(default='')

    resource_uid = columns.UUID(required=False)

    resource_url = columns.Text(default='')

    resource_name = columns.Text(default='')

    status = columns.Text(default='draft')

    max_score = columns.Float(default=10.0)

    is_deleted = columns.Boolean(default=False)

    due_date = columns.DateTime(required=False)

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
