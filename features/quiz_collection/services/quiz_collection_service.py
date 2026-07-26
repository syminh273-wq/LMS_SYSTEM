from features.quiz_collection.repositories import (
    QuizCollectionRepository,
    QuizCollectionAssignmentRepository,
)


class QuizCollectionService:
    def __init__(self):
        self.repository = QuizCollectionRepository()
        self.assignment_repo = QuizCollectionAssignmentRepository()

    def get_by_teacher(self, teacher_id):
        return self.repository.list_for_owner(teacher_id)

    def get_for_classroom(self, classroom_id):
        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        collection_ids = [str(a.collection_id) for a in assignments]
        return [self.repository.get(uid) for uid in collection_ids if self.repository.get(uid)]

    def get_detail(self, collection_id):
        collection = self.repository.get(collection_id)
        if not collection:
            return None
        assignments = self.assignment_repo.get_by_collection(collection_id)
        return {
            'collection': collection,
            'items': self.repository.get_item_quiz_ids(collection),
            'assignments': assignments,
        }

    def create(self, created_by, title, description='', certificate_id=None):
        return self.repository.create(
            created_by=created_by,
            title=title,
            description=description,
            certificate_id=certificate_id,
            status='draft',
        )

    def update(self, instance, **kwargs):
        return self.repository.update_meta(instance, **kwargs)

    def delete(self, instance):
        for assignment in self.assignment_repo.get_by_collection(instance.uid):
            self.assignment_repo.unassign(instance.uid, assignment.classroom_id)
        self.repository.soft_delete(instance)

    def add_quizzes(self, collection_id, quiz_ids: list):
        collection = self.repository.get(collection_id)
        if not collection:
            return []
        existing = {str(q) for q in (collection.item_quiz_ids or [])}
        added = []
        for qid in quiz_ids:
            qid_str = str(qid)
            if qid_str in existing or qid_str in added:
                continue
            self.repository.add_item(collection, qid_str)
            added.append(qid_str)
        return added

    def remove_quiz(self, collection_id, quiz_id):
        collection = self.repository.get(collection_id)
        if not collection:
            return
        self.repository.remove_item(collection, quiz_id)

    def reorder(self, collection_id, ordered_quiz_ids: list):
        collection = self.repository.get(collection_id)
        if not collection:
            return
        self.repository.reorder_items(collection, ordered_quiz_ids)

    def assign_to_classroom(self, collection_id, classroom_id, assigned_by):
        return self.assignment_repo.assign(collection_id, classroom_id, assigned_by)

    def unassign_from_classroom(self, collection_id, classroom_id):
        self.assignment_repo.unassign(collection_id, classroom_id)
