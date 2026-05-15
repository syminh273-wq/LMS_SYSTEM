from core.repositories.base_repository import BaseRepository
from features.sharing.models import Link

class LinkRepository(BaseRepository):
    model = Link

    def get_by_code(self, code: str):
        return self.filter(code=code, is_deleted=False).first()

    def get_by_resource(self, resource_type: str, resource_id):
        return self.filter(resource_type=resource_type, resource_id=resource_id, is_deleted=False)
