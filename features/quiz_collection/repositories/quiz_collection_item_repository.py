from datetime import datetime
from uuid import UUID

from features.quiz_collection.models import QuizCollectionItem


class QuizCollectionItemRepository:

    def get_by_collection(self, collection_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        return list(
            QuizCollectionItem.objects.filter(collection_id=c_id, is_deleted=False)
            .order_by('order')
        )

    def get_quiz_ids(self, collection_id) -> list:
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        items = QuizCollectionItem.objects.filter(collection_id=c_id, is_deleted=False).all()
        return [str(i.quiz_id) for i in items]

    def find_item(self, collection_id, quiz_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        return QuizCollectionItem.objects.filter(
            collection_id=c_id, quiz_id=q_id, is_deleted=False
        ).first()

    def exists(self, collection_id, quiz_id) -> bool:
        return self.find_item(collection_id, quiz_id) is not None

    def add(self, collection_id, quiz_id, order: int) -> QuizCollectionItem:
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        return QuizCollectionItem.objects.create(
            collection_id=c_id,
            quiz_id=q_id,
            order=order,
            added_at=datetime.now(),
        )

    def remove(self, collection_id, quiz_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        item = QuizCollectionItem.objects.filter(
            collection_id=c_id, quiz_id=q_id
        ).first()
        if item:
            item.soft_delete()

    def update_order(self, collection_id, quiz_id, order: int):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        QuizCollectionItem.objects.filter(
            collection_id=c_id, quiz_id=q_id
        ).update(order=order)
