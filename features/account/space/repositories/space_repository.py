from core.repositories.base_repository import BaseRepository
from features.account.space.models import Space


class Repository(BaseRepository):
    model = Space

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
