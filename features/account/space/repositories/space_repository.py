from core.repositories.base_repository import BaseRepository
from features.account.space.models import Space


class Repository(BaseRepository):
    model = Space

    def get_by_slug(self, slug: str):
        instance = self.filter(slug=slug, is_deleted=False).first()
        if instance is None:
            raise Space.DoesNotExist('Space not found.')
        return instance

    def get_by_owner(self, owner_uid):
        return self.filter(owner_uid=owner_uid, is_deleted=False)

    def get_active(self):
        return self.filter(is_active=True, is_deleted=False)
