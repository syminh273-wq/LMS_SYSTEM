from core.repositories.base_repository import BaseRepository

from dummy.models import Dummy


class Repository(BaseRepository):
    model = Dummy

    def get_by_owner(self, owner_id):
        return self.filter(owner_id=owner_id, is_deleted=False)
