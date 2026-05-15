from core.repositories.base_repository import BaseRepository
from features.resource.models.resource import Resource

class ResourceRepository(BaseRepository):
    model = Resource

    def get_by_owner(self, owner_id):
        return self.filter(owner_id=owner_id, is_deleted=False)

    def get_by_type(self, file_type):
        return self.filter(file_type=file_type, is_deleted=False)
