from datetime import datetime
from uuid import UUID

from features.quiz_collection.models import QuizCollection
from core.repositories.base_repository import BaseRepository


def _u(v):
    return UUID(str(v)) if not isinstance(v, UUID) else v


class QuizCollectionRepository(BaseRepository):
    model = QuizCollection

    def get(self, uid):
        return QuizCollection.objects.filter(uid=_u(uid), is_deleted=False).first()

    def list_for_owner(self, owner_id):
        o = _u(owner_id)
        return list(QuizCollection.objects.filter(created_by=o, is_deleted=False))

    def create(self, *, created_by, title, description='', certificate_id=None, status='draft'):
        from core.utils.uuid import uuid7
        return QuizCollection.create(
            uid=uuid7(),
            created_by=_u(created_by),
            title=title,
            description=description,
            certificate_id=_u(certificate_id) if certificate_id else None,
            status=status,
            item_quiz_ids=[],
            quiz_count=0,
        )

    def update_meta(self, instance, **fields):
        for k, v in fields.items():
            setattr(instance, k, v)
        instance.updated_at = datetime.utcnow()
        instance.save()
        return instance

    def soft_delete(self, instance):
        instance.is_deleted = True
        instance.deleted_at = datetime.utcnow()
        instance.save()
        return instance

    def add_item(self, instance, quiz_id, order: int = None):
        qid = _u(quiz_id)
        items = list(instance.item_quiz_ids or [])
        if qid in items:
            return instance
        if order is None or order >= len(items):
            items.append(qid)
        else:
            items.insert(max(0, order), qid)
        instance.item_quiz_ids = items
        instance.quiz_count = len(items)
        instance.updated_at = datetime.utcnow()
        instance.save()
        return instance

    def remove_item(self, instance, quiz_id):
        qid = _u(quiz_id)
        items = [i for i in (instance.item_quiz_ids or []) if i != qid]
        instance.item_quiz_ids = items
        instance.quiz_count = len(items)
        instance.updated_at = datetime.utcnow()
        instance.save()
        return instance

    def reorder_items(self, instance, ordered_quiz_ids):
        ids = [_u(q) for q in ordered_quiz_ids]
        existing = list(instance.item_quiz_ids or [])
        if set(ids) != set(existing):
            return instance
        instance.item_quiz_ids = ids
        instance.updated_at = datetime.utcnow()
        instance.save()
        return instance

    def get_item_quiz_ids(self, instance):
        return list(instance.item_quiz_ids or [])
