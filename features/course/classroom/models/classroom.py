from django.utils.functional import cached_property
from core.utils.uuid import uuid7
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel

class Classroom(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    pid = columns.Text(index=True)
    name = columns.Text(required=True)
    description = columns.Text(default='')
    teacher_id = columns.UUID(index=True, required=True)
    max_students = columns.Integer(default=0)
    status = columns.Text(default='active')

    class Meta:
        get_pk_field = 'uid'

    @cached_property
    def resolve_link(self):
        from features.sharing.repositories.link_repository import LinkRepository
        from features.sharing.serializers.link_response_serializer import LinkResponseSerializer
        from features.sharing.enums.resource_type import ResourceType

        repo = LinkRepository()
        link = repo.get_by_resource(
            resource_type=ResourceType.CLASSROOM.value,
            resource_id=self.uid
        ).first()

        if link:
            return LinkResponseSerializer(link).data
        return None

    __table_name__ = 'account_classrooms'
