from django.utils.functional import cached_property
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Course(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    pid = columns.Text(index=True)
    name = columns.Text(required=True)
    description = columns.Text(default='')
    cover_url = columns.Text(default='')
    teacher_id = columns.UUID(index=True, required=True)
    pricing_type = columns.Text(default='free')
    price_vnd = columns.BigInt(default=0)
    status = columns.Text(default='draft')
    classroom_uid = columns.UUID(index=True, required=False)

    class Meta:
        get_pk_field = 'uid'

    @cached_property
    def resolve_link(self):
        from features.sharing.repositories.link_repository import LinkRepository
        from features.sharing.serializers.link_response_serializer import LinkResponseSerializer

        repo = LinkRepository()
        link = repo.get_by_resource(
            resource_type='course',
            resource_id=self.uid
        ).first()

        if link:
            return LinkResponseSerializer(link).data
        return None

    __table_name__ = 'course_courses'
