from core.services.base_service import BaseService

from dummy.repositories import Repository


class Service(BaseService):
    def __init__(self):
        self.repository = Repository()

    def list_by_owner(self, owner_id):
        return self.repository.get_by_owner(owner_id)

    def create_dummy(self, owner_id, data: dict):
        return self.repository.create(owner_id=owner_id, **data)
