from core.repositories.base_repository import BaseRepository
from features.ranking.models.xp_rule import XPRule


class XPRuleRepository(BaseRepository):
    model = XPRule

    def get(self, event_type):
        return self.model.objects(bucket=0, event_type=event_type).first()

    def all_active(self):
        rows = list(self.model.objects(bucket=0))
        return [r for r in rows if r.is_active]

    def get_amount(self, event_type, default=0):
        rule = self.get(event_type)
        if rule and rule.is_active:
            return int(rule.xp_amount or 0)
        return default

    def upsert(self, event_type, xp_amount, is_active=True, description=''):
        existing = self.get(event_type)
        if existing:
            existing.xp_amount = int(xp_amount)
            existing.is_active = bool(is_active)
            existing.description = description or existing.description
            existing.save()
            return existing
        return self.model.create(
            bucket=0,
            event_type=event_type,
            xp_amount=int(xp_amount),
            is_active=bool(is_active),
            description=description or '',
        )
