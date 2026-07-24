from uuid import UUID
from cassandra.cqlengine import columns

from core.repositories.base_repository import BaseRepository
from features.account.consumer.models.address import Address


class AddressRepository(BaseRepository):
    model = Address

    def get_by_owner(self, owner_id, owner_type: str):
        """Return the single Address row for (owner_id, owner_type), or None."""
        try:
            uid = UUID(str(owner_id))
        except (TypeError, ValueError):
            return None
        return (
            self.model.objects
            .filter(owner_id=uid, owner_type=owner_type, is_deleted=False)
            .allow_filtering()
            .first()
        )

    def get_by_uid(self, uid):
        try:
            return self.model.objects.filter(uid=UUID(str(uid)), is_deleted=False).first()
        except (TypeError, ValueError):
            return None

    def upsert(self, owner_id, owner_type: str, data: dict) -> Address:
        """Create if missing, otherwise update the existing row for this owner."""
        instance = self.get_by_owner(owner_id, owner_type)
        if instance is None:
            payload = {
                'owner_id':   UUID(str(owner_id)),
                'owner_type': owner_type,
                **data,
            }
            instance = self.create(**payload)
        else:
            for k, v in data.items():
                setattr(instance, k, v)
            instance.save()
        return instance

    def soft_delete_by_uid(self, uid) -> bool:
        instance = self.get_by_uid(uid)
        if not instance:
            return False
        instance.soft_delete()
        return True
