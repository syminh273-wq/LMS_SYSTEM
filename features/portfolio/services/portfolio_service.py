import json
import uuid
from rest_framework import exceptions
from features.account.consumer.models.consumer import Consumer
from features.account.space.models.space import Space
from features.portfolio.models import Portfolio
from features.portfolio.repositories import PortfolioRepository


class PortfolioService:
    SINGLE_KEYS = {'intro'}

    def __init__(self):
        self.repository = PortfolioRepository()

    @staticmethod
    def resolve_owner_type(user) -> str:
        if isinstance(user, Space):
            return 'space'
        if isinstance(user, Consumer):
            return 'consumer'
        raise exceptions.PermissionDenied('Only Space or Consumer accounts can manage a portfolio.')

    @staticmethod
    def resolve_owner(user):
        if isinstance(user, (Space, Consumer)):
            return user.uid, PortfolioService.resolve_owner_type(user)
        raise exceptions.PermissionDenied('Invalid user type.')

    def list_for_owner(self, owner_id, owner_type, include_private=False):
        if isinstance(owner_id, str):
            owner_id = uuid.UUID(owner_id)
        rows = self.repository.list_by_owner(owner_id, owner_type, include_private=include_private)
        if not rows:
            for fallback_type in Portfolio.OWNER_TYPES:
                if fallback_type == owner_type:
                    continue
                rows = self.repository.list_by_owner(owner_id, fallback_type, include_private=include_private)
                if rows:
                    break
        return self._group_by_key(rows)

    def get_mine(self, user):
        owner_id, owner_type = self.resolve_owner(user)
        return self.list_for_owner(owner_id, owner_type, include_private=True)

    def get_public(self, owner_type, owner_id):
        if owner_type not in Portfolio.OWNER_TYPES:
            raise exceptions.ValidationError({'owner_type': 'Invalid owner type.'})
        if isinstance(owner_id, str):
            try:
                owner_id = uuid.UUID(owner_id)
            except (ValueError, TypeError, AttributeError):
                raise exceptions.ValidationError({'owner_id': 'Invalid owner id.'})
        return self.list_for_owner(owner_id, owner_type, include_private=False)

    def upsert_entry(self, user, data: dict):
        owner_id, owner_type = self.resolve_owner(user)
        key = data.get('key')
        if key not in Portfolio.VALID_KEYS:
            raise exceptions.ValidationError({'key': f"key must be one of {Portfolio.VALID_KEYS}"})

        if key in self.SINGLE_KEYS:
            existing = self._find_single(owner_id, owner_type, key)
            if existing and not data.get('uid'):
                data['uid'] = existing.uid

        value = data.get('value')
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif not isinstance(value, str):
            raise exceptions.ValidationError({'value': 'value must be a JSON object/string.'})

        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise exceptions.ValidationError({'value': 'value must be valid JSON.'})

        return self.repository.upsert(
            owner_id=owner_id,
            owner_type=owner_type,
            key=key,
            value=value,
            is_public=data.get('is_public', True),
            display_order=data.get('display_order', 0),
            uid=data.get('uid'),
        )

    def bulk_upsert(self, user, entries):
        if not isinstance(entries, list):
            raise exceptions.ValidationError({'entries': 'entries must be a list.'})
        owner_id, owner_type = self.resolve_owner(user)
        prepared = []
        for entry in entries:
            key = entry.get('key')
            if key not in Portfolio.VALID_KEYS:
                raise exceptions.ValidationError({'key': f"key must be one of {Portfolio.VALID_KEYS}"})
            value = entry.get('value')
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            try:
                json.loads(value)
            except (TypeError, json.JSONDecodeError):
                raise exceptions.ValidationError({'value': 'value must be valid JSON.'})
            prepared.append({
                'uid': entry.get('uid'),
                'key': key,
                'value': value,
                'is_public': entry.get('is_public', True),
                'display_order': entry.get('display_order', 0),
            })
        self.repository.bulk_upsert(owner_id, owner_type, prepared)
        return self.get_mine(user)

    def delete_entry(self, user, uid):
        owner_id, owner_type = self.resolve_owner(user)
        instance = self.repository.get_entry(uid)
        if instance.owner_id != owner_id or instance.owner_type != owner_type:
            raise exceptions.PermissionDenied('You can only delete your own portfolio entries.')
        self.repository.soft_delete(instance)
        return True

    def reorder(self, user, orders):
        owner_id, owner_type = self.resolve_owner(user)
        self.repository.update_orders(owner_id, owner_type, orders)
        return self.get_mine(user)

    def _find_single(self, owner_id, owner_type, key):
        rows = self.repository.list_by_owner(owner_id, owner_type, include_private=True)
        for row in rows:
            if row.key == key:
                return row
        return None

    def _group_by_key(self, rows):
        grouped = {
            'intro': None,
            'certificate': [],
            'experience': [],
            'achievement': [],
            'course': [],
            'education': [],
        }
        sorted_rows = sorted(rows, key=lambda r: (r.display_order, r.uid))
        for row in sorted_rows:
            item = self._serialize_row(row)
            if row.key in self.SINGLE_KEYS:
                grouped[row.key] = item
            elif row.key in grouped:
                grouped[row.key].append(item)
        return grouped

    def _serialize_row(self, row):
        try:
            value = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            value = {}
        return {
            'uid': str(row.uid),
            'key': row.key,
            'value': value,
            'is_public': row.is_public,
            'display_order': row.display_order,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        }
