import os
import mimetypes
from core.services.base_service import BaseService
from core.storages.storage_service import storage_service
from features.resource.repositories.resource_repository import ResourceRepository

class ResourceService(BaseService):
    def __init__(self):
        self.repository = ResourceRepository()

    def upload_resource(self, file_obj, owner_id=None, owner_type=None, metadata=None):
        """
        Upload a file to R2 and save its metadata to Cassandra.
        """
        # Get file extension for file_type
        filename = file_obj.name
        file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
        if not file_extension:
            mime_type = mimetypes.guess_type(filename)[0]
            if mime_type:
                file_extension = mime_type.split('/')[-1]
            else:
                file_extension = 'unknown'

        from core.utils.uuid import uuid7
        resource_uid = uuid7()
        object_key = f"resources/{resource_uid}/{filename}"

        upload_result = storage_service.upload_fileobj(file_obj, object_key, is_public=True)

        if not upload_result['success']:
            return upload_result

        resource = self.repository.create(
            uid=resource_uid,
            name=filename,
            file_type=file_extension,
            url=upload_result['url'],
            size=file_obj.size,
            owner_id=owner_id,
            owner_type=owner_type,
            metadata=metadata or {}
        )

        return {
            'success': True,
            'data': resource
        }

    def get_by_owner(self, owner_id):
        return self.repository.get_by_owner(owner_id)

    def get_by_type(self, file_type):
        return self.repository.get_by_type(file_type)

    def get_resources(self, owner_id=None, file_type=None):
        filters = {'is_deleted': False}
        if owner_id:
            filters['owner_id'] = owner_id
        if file_type:
            filters['file_type'] = file_type
        return self.repository.filter(**filters)
