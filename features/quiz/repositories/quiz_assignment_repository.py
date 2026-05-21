from uuid import UUID
from features.quiz.models.quiz_assignment import QuizAssignment
from core.repositories.base_repository import BaseRepository


class QuizAssignmentRepository(BaseRepository):
    model = QuizAssignment

    def get_by_quiz(self, quiz_id):
        return list(self.model.objects.filter(quiz_id=quiz_id))

    def get_by_classroom(self, classroom_id):
        return list(self.model.objects.filter(classroom_id=classroom_id).allow_filtering())

    def find_assignment(self, quiz_id, classroom_id):
        try:
            q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
            c_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
            return self.model.objects.filter(quiz_id=q_id, classroom_id=c_id).first()
        except (ValueError, Exception):
            return None

    def assign(self, quiz_id, classroom_id, assigned_by, **kwargs):
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        c_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id

        # Point query với chính xác Primary Key ((quiz_id), classroom_id)
        existing = self.model.objects.filter(quiz_id=q_id, classroom_id=c_id).first()
        
        if existing:
            # Cassandra thực hiện UPSERT dựa trên PK, đảm bảo không trùng lặp
            self.model.objects.filter(quiz_id=q_id, classroom_id=c_id).update(**kwargs)
            return self.model.objects.filter(quiz_id=q_id, classroom_id=c_id).first()

        return self.model.objects.create(
            quiz_id=q_id,
            classroom_id=c_id,
            assigned_by=assigned_by,
            **kwargs
        )

    def update_settings(self, quiz_id, classroom_id, **kwargs) -> QuizAssignment:
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        c_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id

        # Truy vấn trực tiếp bằng PK
        qs = self.model.objects.filter(quiz_id=q_id, classroom_id=c_id)
        if not qs.first():
            # Thử thêm allow_filtering nếu truy vấn PK gặp vấn đề (hiếm gặp nhưng an toàn)
            if not qs.allow_filtering().first():
                raise ValueError(f"Assignment not found for Quiz {q_id} and Classroom {c_id}")

        qs.update(**kwargs)
        return qs.first()

    def unassign(self, quiz_id, classroom_id):
        q_id = UUID(str(quiz_id)) if not isinstance(quiz_id, UUID) else quiz_id
        c_id = UUID(str(classroom_id)) if not isinstance(classroom_id, UUID) else classroom_id
        self.model.objects.filter(quiz_id=q_id, classroom_id=c_id).delete()
