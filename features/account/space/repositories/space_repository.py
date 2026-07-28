from core.repositories.base_repository import BaseRepository
from core.utils.pid import generate_unique_pid
from features.account.space.models import Space


class Repository(BaseRepository):
    model = Space

    def create(self, **kwargs):
        if not kwargs.get('pid'):
            kwargs['pid'] = generate_unique_pid(self.find_by_pid)
        return super().create(**kwargs)

    def get_by_email(self, email: str):
        instance = self.filter(email=email, is_deleted=False).first()
        if instance is None:
            raise Space.DoesNotExist('Space not found.')
        return instance

    def get_by_slug(self, slug: str):
        instance = self.filter(slug=slug, is_deleted=False).first()
        if instance is None:
            raise Space.DoesNotExist('Space not found.')
        return instance

    def get_active(self):
        return self.filter(is_active=True, is_deleted=False)

    def update_profile(self, instance, **kwargs):
        return self.update(instance, **kwargs)

    def save_password(self, instance):
        instance.save()
        return instance

    def find_by_pid(self, pid: str):
        return self.model.objects.filter(pid=pid, is_deleted=False).first()
