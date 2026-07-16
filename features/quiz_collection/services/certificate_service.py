import logging
import os
from urllib.parse import urlparse

from core.services.base_service import BaseService
from core.storages.storage_service import storage_service
from core.utils.uuid import uuid7
from features.quiz_collection.repositories import CertificateRepository

logger = logging.getLogger(__name__)


def _object_key_from_url(url: str) -> str | None:
    if not url:
        return None
    if url.startswith('certificates/'):
        return url
    public_domain = storage_service.public_domain.rstrip('/')
    if public_domain and url.startswith(public_domain):
        return url.replace(public_domain, '', 1).lstrip('/')
    parsed = urlparse(url)
    path = parsed.path.lstrip('/')
    if path.startswith('certificates/'):
        return path
    return None


def _build_object_key(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower() or '.bin'
    return f"certificates/{uuid7()}{ext}"


class CertificateService(BaseService):
    def __init__(self):
        self.repository = CertificateRepository()

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def get_active_by_teacher(self, teacher_id):
        return self.repository.get_active_by_teacher(teacher_id)

    def create(self, created_by, name, description='', template_url=None, template_image=None):
        resolved_url = template_url
        if template_image is not None:
            resolved_url = self._upload_template_image(template_image)
        return self.repository.create(
            created_by=created_by,
            name=name,
            description=description,
            template_url=resolved_url,
            is_active=True,
        )

    def update(self, instance, template_image=None, **kwargs):
        old_template_url = getattr(instance, 'template_url', None)

        if template_image is not None:
            new_url = self._upload_template_image(template_image)
            kwargs['template_url'] = new_url

        is_clearing_url = (
            'template_url' in kwargs
            and kwargs.get('template_url') in (None, '')
            and old_template_url
        )

        if is_clearing_url:
            kwargs['template_url'] = None

        updated = self.repository.update(instance, **kwargs)

        if is_clearing_url:
            self._delete_template_image(old_template_url)
        elif template_image is not None and old_template_url and old_template_url != kwargs.get('template_url'):
            self._delete_template_image(old_template_url)

        return updated

    def delete(self, instance):
        old_template_url = getattr(instance, 'template_url', None)
        self.repository.delete(instance)
        if old_template_url:
            self._delete_template_image(old_template_url)

    def _upload_template_image(self, file_obj) -> str:
        object_key = _build_object_key(file_obj.name)
        result = storage_service.upload_fileobj(file_obj, object_key, is_public=True)
        if not result.get('success'):
            raise ValueError(result.get('message') or 'Upload to storage failed')
        return result['url']

    def _delete_template_image(self, url: str):
        key = _object_key_from_url(url)
        if not key:
            return
        try:
            storage_service.delete_object(key, is_public=True)
        except Exception as exc:
            logger.warning('Failed to delete certificate template from R2: %s', exc)
