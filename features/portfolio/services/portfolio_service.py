import json
import uuid
from rest_framework import exceptions
from features.account.consumer.models.consumer import Consumer
from features.account.space.models.space import Space
from features.portfolio.models import Portfolio
from features.portfolio.repositories import PortfolioRepository
from core.services.base_service import BaseService


class PortfolioService(BaseService):
    """
    Polymorphic key-value profile service.

    Một service duy nhất phục vụ 3 use cases:
      1. get_mine(user) / get_public(...)  — portfolio công khai (rich entries)
      2. get_profile_settings(user)        — thay thế StudentProfileService
      3. get_social_profile(owner_id, ...)  — thay thế phần bio/skills/social của UserProfile
    """

    SINGLE_KEYS = Portfolio.SINGLE_KEYS
    RICH_KEYS = Portfolio.RICH_KEYS
    PRIVACY_KEYS = Portfolio.PRIVACY_KEYS
    APPEARANCE_KEYS = Portfolio.APPEARANCE_KEYS
    PROFILE_KEYS = Portfolio.PROFILE_KEYS

    PROFILE_SETTINGS_DEFAULTS = {
        'bio': '',
        'city': '',
        'country': 'Việt Nam',
        'theme_color': 'indigo',
        'cover_style': 'gradient',
        'cover_value': '',
        'show_stats': True,
        'show_classrooms': True,
        'show_grades': True,
        'show_badges': True,
        'show_address': True,
        'show_links': True,
        'show_hobbies': True,
        'show_certificates': True,
        'show_activity': False,
        'show_contact': False,
        'sections_order': ['classrooms', 'grades', 'certificates', 'about'],
        'profile_visibility': 'class_only',
    }

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

    def get_profile_settings(self, user) -> dict:
        owner_id, owner_type = self.resolve_owner(user)
        return self._build_profile_settings(owner_id, owner_type, include_private=True)

    def get_profile_settings_or_public(self, owner_id) -> dict:
        try:
            oid = uuid.UUID(str(owner_id))
        except (ValueError, TypeError, AttributeError):
            return dict(self.PROFILE_SETTINGS_DEFAULTS, consumer_uid=str(owner_id), address='', updated_at=None)
        for owner_type in Portfolio.OWNER_TYPES:
            data = self._build_profile_settings(oid, owner_type, include_private=False)
            rows = self.repository.list_by_owner(oid, owner_type, include_private=False)
            if rows:
                return data
        return dict(self.PROFILE_SETTINGS_DEFAULTS, consumer_uid=str(oid), address='', updated_at=None)

    def _build_profile_settings(self, owner_id, owner_type, include_private: bool) -> dict:
        rows = self.repository.list_by_owner(owner_id, owner_type, include_private=include_private)
        by_key = {r.key: r for r in rows}

        result = dict(self.PROFILE_SETTINGS_DEFAULTS)
        result['consumer_uid'] = str(owner_id)

        for key, default in self.PROFILE_SETTINGS_DEFAULTS.items():
            row = by_key.get(key)
            if row is None:
                continue
            try:
                parsed = json.loads(row.value)
            except (TypeError, json.JSONDecodeError):
                parsed = default
            if isinstance(default, bool):
                result[key] = bool(parsed)
            elif isinstance(default, list):
                result[key] = parsed if isinstance(parsed, list) else default
            elif isinstance(default, dict):
                result[key] = parsed if isinstance(parsed, dict) else default
            else:
                result[key] = parsed

        result['address'] = ''
        latest = max(
            (getattr(r, 'updated_at', None) for r in rows if getattr(r, 'updated_at', None)),
            default=None,
        )
        result['updated_at'] = latest.isoformat() if latest else None

        return result

    def get_social_profile(self, owner_id, owner_type: str) -> dict:
        if isinstance(owner_id, str):
            try:
                owner_id = uuid.UUID(owner_id)
            except (ValueError, TypeError, AttributeError):
                return {}
        rows = self.repository.list_by_owner(owner_id, owner_type, include_private=True)
        by_key = {r.key: r for r in rows}
        result = {}
        for key in self.PROFILE_KEYS:
            row = by_key.get(key)
            if row is None:
                continue
            try:
                result[key] = json.loads(row.value)
            except (TypeError, json.JSONDecodeError):
                result[key] = row.value
        return result

    def update_profile_settings(self, user, data: dict) -> dict:
        owner_id, owner_type = self.resolve_owner(user)
        allowed = set(self.PROFILE_SETTINGS_DEFAULTS.keys()) - {'consumer_uid'}
        clean = {}
        for k, v in data.items():
            if k in allowed:
                clean[k] = v

        for field in ('sections_order',):
            if field in clean and not isinstance(clean[field], str):
                clean[field] = json.dumps(clean[field], ensure_ascii=False)

        for key, value in clean.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            self.repository.upsert(
                owner_id=owner_id,
                owner_type=owner_type,
                key=key,
                value=value_str,
                is_public=(key not in self.PRIVACY_KEYS),
            )

        return self.get_profile_settings(user)

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
            if row.key in self.RICH_KEYS:
                if row.key == 'intro':
                    grouped['intro'] = item
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
