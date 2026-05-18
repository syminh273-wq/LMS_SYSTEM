import os
import mimetypes
from urllib.parse import urlparse

from core.services.base_service import BaseService
from core.storages.storage_service import storage_service
from features.resource.repositories.resource_repository import ResourceRepository


class ResourceService(BaseService):
    def __init__(self):
        self.repository = ResourceRepository()

    def get_file_extension(self, filename):
        file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
        if file_extension:
            return file_extension

        mime_type = mimetypes.guess_type(filename)[0]
        if mime_type:
            return mime_type.split('/')[-1]

        return 'unknown'

    def build_object_key(self, resource_uid, filename):
        return f"resources/{resource_uid}/{filename}"

    def resolve_object_key(self, url):
        if not url:
            return None

        if url.startswith('resources/'):
            return url

        public_domain = storage_service.public_domain.rstrip('/')
        if public_domain and url.startswith(public_domain):
            return url.replace(public_domain, '', 1).lstrip('/')

        parsed = urlparse(url)
        path = parsed.path.lstrip('/')
        if path.startswith('resources/'):
            return path

        return None

    def upload_resource(self, file_obj, owner_id=None, owner_type=None, metadata=None):
        """
        Upload a file to R2 and save its metadata to Cassandra.
        """
        filename = file_obj.name
        file_extension = self.get_file_extension(filename)

        from core.utils.uuid import uuid7
        resource_uid = uuid7()
        object_key = self.build_object_key(resource_uid, filename)

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

    def reupload_resource(self, resource, file_obj, metadata=None):
        filename = file_obj.name
        file_extension = self.get_file_extension(filename)
        object_key = self.build_object_key(resource.uid, filename)
        old_object_key = self.resolve_object_key(resource.url)

        upload_result = storage_service.upload_fileobj(file_obj, object_key, is_public=True)
        if not upload_result['success']:
            return upload_result

        update_data = {
            'name': filename,
            'file_type': file_extension,
            'url': upload_result['url'],
            'size': file_obj.size,
        }
        if metadata is not None:
            update_data['metadata'] = metadata

        updated_resource = self.repository.update(resource, **update_data)

        if old_object_key and old_object_key != object_key:
            storage_service.delete_object(old_object_key, is_public=True)

        return {
            'success': True,
            'data': updated_resource
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
