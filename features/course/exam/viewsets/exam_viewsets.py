from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from features.course.exam.services import ExamService


def serialize_exam(exam):
    return {
        "uid": str(exam.uid),
        "classroom_id": str(exam.classroom_id),
        "teacher_id": str(exam.teacher_id),
        "title": exam.title,
        "description": exam.description,
        "content_type": exam.content_type,
        "content": exam.content,
        "resource_uid": str(exam.resource_uid) if exam.resource_uid else None,
        "resource_url": exam.resource_url,
        "resource_name": exam.resource_name,
        "status": exam.status,
        "due_date": exam.due_date.isoformat() if exam.due_date else None,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "updated_at": exam.updated_at.isoformat() if exam.updated_at else None,
    }


class SpaceExamViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exam_service = ExamService()

    def get(self, request, uid=None):
        teacher_id = request.user.uid

        if uid:
            exam = self.exam_service.get_exam(uid)
            return Response(serialize_exam(exam))

        classroom_id = request.query_params.get("classroom_id")
        exams = self.exam_service.list_teacher_exams(
            teacher_id=teacher_id,
            classroom_id=classroom_id,
        )
        return Response([serialize_exam(exam) for exam in exams])

    def post(self, request):
        teacher_id = request.user.uid
        exam = self.exam_service.create_exam(teacher_id, request.data.copy())
        return Response(serialize_exam(exam), status=status.HTTP_201_CREATED)

    def put(self, request, uid):
        exam = self.exam_service.update_exam(uid, request.data.copy())
        return Response(serialize_exam(exam))

    def delete(self, request, uid):
        self.exam_service.delete_exam(uid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsumerClassroomExamViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exam_service = ExamService()

    def get(self, request, uid):
        exams = self.exam_service.list_student_exams(uid)
        return Response([serialize_exam(exam) for exam in exams])


class ConsumerExamListViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exam_service = ExamService()

    def get(self, request):
        classroom_id = request.query_params.get("classroom_id")
        exams = self.exam_service.list_student_exams(classroom_id)
        return Response([serialize_exam(exam) for exam in exams])
