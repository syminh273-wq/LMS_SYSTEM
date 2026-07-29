from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from core.search_engine.typesense.service import TypesenseService
from core.views.mixins import SpaceScopeMixin
from features.account.consumer.repositories import ConsumerRepository
from features.course.classroom.repositories.teacher_contact_repository import TeacherContactRepository
from features.course.classroom.repositories import Repository as ClassroomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository


def _consumer_summary(consumer):
    if not consumer:
        return {'full_name': '', 'email': '', 'avatar_url': ''}
    return {
        'full_name': getattr(consumer, 'full_name', '') or '',
        'email': getattr(consumer, 'email', '') or '',
        'avatar_url': getattr(consumer, 'avatar_url', '') or '',
    }


class TeacherStudentSearchView(SpaceScopeMixin, APIView):
    """
    Full-text search over students in this teacher's org scope.
    @param q: search query (required)
    @param limit: max results, default 20
    @param offset: pagination offset, default 0
    @return: total_hits, results
    """

    def get(self, request):
        query = (request.query_params.get('q') or '').strip()
        if not query:
            return Response({'error': 'q is required'}, status=400)

        limit  = min(int(request.query_params.get('limit',  20)), 50)
        offset = max(int(request.query_params.get('offset',  0)),  0)

        contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
        uids = [str(c.consumer_uid) for c in contacts]
        if not uids:
            return Response({'total_hits': 0, 'results': []})

        filter_by = f'uid:["' + '","'.join(uids) + '"]'
        try:
            resp = TypesenseService().search(
                collection='lms_consumer',
                query=query,
                query_by=['full_name', 'first_name', 'last_name', 'email', 'username'],
                filter_by=filter_by,
                limit=limit,
                offset=offset,
            )
            return Response(resp.to_dict())
        except Exception as exc:
            return Response({'total_hits': 0, 'results': [], 'error': str(exc)})


class TeacherStudentListView(SpaceScopeMixin, APIView):
    """
    List all unique students who ever studied with the authenticated teacher.
    @return: list of students with first_joined_at
    """

    def get(self, request):
        contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
        consumer_repo = ConsumerRepository()
        out = []
        for c in contacts:
            consumer = consumer_repo.find(c.consumer_uid)
            summary = _consumer_summary(consumer)
            out.append({
                'consumer_uid':    str(c.consumer_uid),
                'consumer_name':   summary['full_name'],
                'consumer_email':  summary['email'],
                'consumer_avatar': summary['avatar_url'],
                'first_joined_at': c.first_joined_at.isoformat() if c.first_joined_at else None,
            })
        return Response(out)


class TeacherStudentDetailView(SpaceScopeMixin, APIView):
    """
    Get a student's profile and their stats across the teacher's classrooms.
    @param consumer_uid: the student to look up
    @return: consumer profile, classrooms with join/exam stats
    """

    def get(self, request, consumer_uid):
        contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
        contact = next((c for c in contacts if str(c.consumer_uid) == consumer_uid), None)
        if not contact:
            raise NotFound("Student not found in your contacts.")

        consumer = ConsumerRepository().find(consumer_uid)
        summary = _consumer_summary(consumer)

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
                'full_name':      summary['full_name'],
                'email':          summary['email'],
                'avatar_url':     summary['avatar_url'],
                'first_joined_at': contact.first_joined_at.isoformat() if contact.first_joined_at else None,
            },
            'classrooms': classroom_rows,
        })
