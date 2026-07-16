from core.services.base_service import BaseService
from features.quiz_collection.repositories import (
    QuizCollectionRepository,
    QuizCollectionItemRepository,
    QuizCollectionAssignmentRepository,
)


class QuizCollectionService(BaseService):
    def __init__(self):
        self.repository = QuizCollectionRepository()
        self.item_repo = QuizCollectionItemRepository()
        self.assignment_repo = QuizCollectionAssignmentRepository()

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def get_for_classroom(self, classroom_id):
        assignments = self.assignment_repo.get_by_classroom(classroom_id)
        collection_ids = [str(a.collection_id) for a in assignments]
        return self.repository.get_by_uids(collection_ids)

    def get_detail(self, collection_id):
        collection = self.repository.find(collection_id)
        items = self.item_repo.get_by_collection(collection_id)
        assignments = self.assignment_repo.get_by_collection(collection_id)
        return {
            'collection': collection,
            'items': items,
            'assignments': assignments,
        }

    def create(self, created_by, title, description='', certificate_id=None):
        return self.repository.create(
            created_by=created_by,
            title=title,
            description=description,
            certificate_id=certificate_id,
            quiz_count=0,
            status='draft',
        )

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance):
        for item in self.item_repo.get_by_collection(instance.uid):
            self.item_repo.remove(instance.uid, item.quiz_id)
        for assignment in self.assignment_repo.get_by_collection(instance.uid):
            self.assignment_repo.unassign(instance.uid, assignment.classroom_id)
        self.repository.delete(instance)

    def add_quizzes(self, collection_id, quiz_ids: list):
        existing = set(self.item_repo.get_quiz_ids(collection_id))
        added = []
        for idx, qid in enumerate(quiz_ids):
            qid_str = str(qid)
            if qid_str in existing:
                continue
            order = len(existing) + len(added)
            self.item_repo.add(collection_id, qid_str, order)
            added.append(qid_str)
        new_count = len(existing) + len(added)
        self.repository.update(self.repository.find(collection_id), quiz_count=new_count)
        return added

    def remove_quiz(self, collection_id, quiz_id):
        self.item_repo.remove(collection_id, quiz_id)
        items = self.item_repo.get_by_collection(collection_id)
        for idx, item in enumerate(items):
            self.item_repo.update_order(collection_id, item.quiz_id, idx)
        self.repository.update(self.repository.find(collection_id), quiz_count=len(items))

    def reorder(self, collection_id, ordered_quiz_ids: list):
        for idx, qid in enumerate(ordered_quiz_ids):
            self.item_repo.update_order(collection_id, qid, idx)

    def assign_to_classroom(self, collection_id, classroom_id, assigned_by):
        return self.assignment_repo.assign(collection_id, classroom_id, assigned_by)

    def unassign_from_classroom(self, collection_id, classroom_id):
        self.assignment_repo.unassign(collection_id, classroom_id)
