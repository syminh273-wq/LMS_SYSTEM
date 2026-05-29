from uuid import UUID

from features.course.exam.models.exam_session import ExamSession


class ExamSessionRepository:
    def create(self, **data):
        # bucket=0 mặc định từ model
        return ExamSession.create(**data)

    def get_by_uid(self, uid):
        try:
            return ExamSession.objects(bucket=0, uid=UUID(str(uid))).first()
        except Exception:
            return None

    def get_by_token(self, token):
        # Dùng bucket=0 để tối ưu query nếu có thể, hoặc dùng filter
        return ExamSession.objects.filter(bucket=0, token=token).allow_filtering().first()

    def get_by_student(self, exam_id, student_id):
        try:
            results = ExamSession.objects.filter(
                bucket=0,
                exam_id=UUID(str(exam_id)),
                student_id=UUID(str(student_id))
            ).allow_filtering()
            return results.first()
        except Exception:
            return None

    def list_by_exam(self, exam_id):
        try:
            return list(ExamSession.objects.filter(bucket=0, exam_id=UUID(str(exam_id))))
        except Exception:
            return []

    def update(self, session, **data):
        for k, v in data.items():
            setattr(session, k, v)
        session.save()
        return session
