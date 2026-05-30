from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from core.search_engine.typesense.service import TypesenseService
from core.views.mixins import UserScopeMixin
from features.course.classroom.repositories.teacher_contact_repository import TeacherContactRepository
from features.course.classroom.repositories import Repository as ClassroomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository


class TeacherStudentSearchView(UserScopeMixin, APIView):
    """GET /api/v1/space/course/students/search/?q=...
    Full-text search over students in this teacher's org scope (lms_teacher_contact).
    teacher_id is always injected into filter — teacher can only see their own students.
    """

    def get(self, request):
        query = (request.query_params.get('q') or '').strip()
        if not query:
            return Response({'error': 'q is required'}, status=400)

        limit  = min(int(request.query_params.get('limit',  20)), 50)
        offset = max(int(request.query_params.get('offset',  0)),  0)

        filter_by = f"teacher_id:{request.user.uid}"

        try:
            resp = TypesenseService().search(
                collection='lms_teacher_contact',
                query=query,
                query_by=['consumer_name', 'first_name', 'last_name', 'consumer_email'],
                filter_by=filter_by,
                limit=limit,
                offset=offset,
            )
            return Response(resp.to_dict())
        except Exception as exc:
            return Response({'total_hits': 0, 'results': [], 'error': str(exc)})


class TeacherStudentListView(UserScopeMixin, APIView):
    """GET /api/v1/space/course/students/
    All unique students who ever studied with the authenticated teacher.
    """

    def get(self, request):
        contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
        return Response([
            {
                'consumer_uid':    str(c.consumer_uid),
                'consumer_name':   c.consumer_name,
                'consumer_email':  c.consumer_email,
                'consumer_avatar': c.consumer_avatar,
                'first_joined_at': c.first_joined_at.isoformat() if c.first_joined_at else None,
            }
            for c in contacts
        ])


class TeacherStudentDetailView(UserScopeMixin, APIView):
    """GET /api/v1/space/course/students/<consumer_uid>/
    Student profile + list of teacher's classrooms the student joined, with stats.
    """

    def get(self, request, consumer_uid):
        contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
        contact = next((c for c in contacts if str(c.consumer_uid) == consumer_uid), None)
        if not contact:
            raise NotFound("Student not found in your contacts.")

        classrooms = ClassroomRepository().get_by_teacher(request.user.uid)
        member_repo = ClassroomMemberRepository()
        exam_repo = ExamRepository()
        sub_repo = ExamSubmissionRepository()

        classroom_rows = []
        for classroom in classrooms:
            member = member_repo.get_member(classroom.uid, consumer_uid)
            if not member or member.is_deleted or member.status != 'approved':
                continue

            exams = list(exam_repo.list_by_classroom(classroom.uid))
            submitted = 0
            grade_sum = 0.0
            grade_count = 0
            for exam in exams:
                subs = sub_repo.list_by_exam_and_student(exam.uid, consumer_uid)
                if subs:
                    submitted += 1
                    grade = getattr(subs[0], 'grade', None)
                    if grade is not None:
                        grade_sum += float(grade)
                        grade_count += 1

            classroom_rows.append({
                'classroom': {
                    'uid':         str(classroom.uid),
                    'name':        classroom.name,
                    'description': classroom.description,
                    'status':      classroom.status,
                    'pid':         classroom.pid,
                },
                'joined_at':       member.joined_at.isoformat() if member.joined_at else None,
                'total_exams':     len(exams),
                'submitted_count': submitted,
                'avg_grade':       round(grade_sum / grade_count, 1) if grade_count else None,
            })

        return Response({
            'consumer': {
                'uid':            str(contact.consumer_uid),
                'full_name':      contact.consumer_name,
                'email':          contact.consumer_email,
                'avatar_url':     contact.consumer_avatar,
                'first_joined_at': contact.first_joined_at.isoformat() if contact.first_joined_at else None,
            },
            'classrooms': classroom_rows,
        })
