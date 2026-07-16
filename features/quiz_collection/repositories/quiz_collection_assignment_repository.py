from uuid import UUID

from features.quiz_collection.models import QuizCollectionAssignment


class QuizCollectionAssignmentRepository:

    def get_by_collection(self, collection_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        return list(
            QuizCollectionAssignment.objects.filter(collection_id=c_id, is_deleted=False)
        )

    def get_by_classroom(self, classroom_id):
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        return list(
            QuizCollectionAssignment.objects.filter(classroom_id=r_id, is_deleted=False)
            .allow_filtering()
        )

    def find_assignment(self, collection_id, classroom_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        return QuizCollectionAssignment.objects.filter(
            collection_id=c_id, classroom_id=r_id, is_deleted=False
        ).first()

    def assign(self, collection_id, classroom_id, assigned_by) -> QuizCollectionAssignment:
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id

        existing = QuizCollectionAssignment.objects.filter(
            collection_id=c_id, classroom_id=r_id
        ).first()

        if existing:
            if existing.is_deleted:
                existing.update(is_deleted=False, deleted_at=None)
            return existing

        return QuizCollectionAssignment.objects.create(
            collection_id=c_id,
            classroom_id=r_id,
            assigned_by=assigned_by,
        )

    def unassign(self, collection_id, classroom_id):
        c_id = UUID(str(collection_id)) if not isinstance(collection_id, UUID) else collection_id
        r_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        item = QuizCollectionAssignment.objects.filter(
            collection_id=c_id, classroom_id=r_id
        ).first()
        if item:
            item.soft_delete()
