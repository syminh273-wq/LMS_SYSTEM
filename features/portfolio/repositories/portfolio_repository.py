import uuid
from datetime import datetime
from core.repositories.base_repository import BaseRepository
from features.portfolio.models import Portfolio


class PortfolioRepository(BaseRepository):
    model = Portfolio

    def list_by_owner(self, owner_id, owner_type, include_private=False):
        qs = self.filter(owner_id=owner_id, owner_type=owner_type, is_deleted=False)
        if not include_private:
            qs = self._filter_qs(qs, is_public=True)
        return list(qs)

    def get_entry(self, uid):
        instance = self.find(uid)
        return instance

    def soft_delete(self, instance):
        instance.is_deleted = True
        instance.deleted_at = datetime.utcnow()
        instance.save()
        return instance

    def upsert(self, owner_id, owner_type, key, value, is_public=True, display_order=0, uid=None):
        if uid:
            try:
                instance = self.find(uid)
                if instance.owner_id != owner_id or instance.owner_type != owner_type:
                    raise Portfolio.DoesNotExist('Entry not found.')
                instance.key = key
                instance.value = value
                instance.is_public = is_public
                instance.display_order = display_order
                instance.updated_at = datetime.utcnow()
                instance.save()
                return instance
            except Portfolio.DoesNotExist:
                pass

        return Portfolio.create(
            uid=uuid.uuid4(),
            owner_id=owner_id,
            owner_type=owner_type,
            key=key,
            value=value,
            is_public=is_public,
            display_order=display_order,
            updated_at=datetime.utcnow(),
        )

    def bulk_upsert(self, owner_id, owner_type, entries):
        results = []
        for entry in entries:
            uid = entry.get('uid')
            results.append(
                self.upsert(
                    owner_id=owner_id,
                    owner_type=owner_type,
                    key=entry['key'],
                    value=entry['value'],
                    is_public=entry.get('is_public', True),
                    display_order=entry.get('display_order', 0),
                    uid=uid,
                )
            )
        return results

    def update_orders(self, owner_id, owner_type, orders):
        for item in orders:
            try:
                instance = self.find(item['uid'])
                if instance.owner_id != owner_id or instance.owner_type != owner_type:
                    continue
                instance.display_order = item.get('display_order', 0)
                instance.updated_at = datetime.utcnow()
                instance.save()
            except Portfolio.DoesNotExist:
                continue
        return True
