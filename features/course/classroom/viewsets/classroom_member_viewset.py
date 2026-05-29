from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from core.views.mixins import UserScopeMixin
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_member_service import ClassroomMemberService
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService


class ClassroomMemberViewSet(UserScopeMixin, ViewSet):

    def _serialize_member(self, m):
        return {
            'member_id': str(m.member_id),
            'member_type': m.member_type,
            'member_name': m.member_name,
            'member_avatar': m.member_avatar or '',
            'role': m.role,
            'status': getattr(m, 'status', 'approved'),
            'joined_at': m.joined_at.isoformat() if m.joined_at else None,
        }

    def list(self, request, classroom_uid=None):
        """GET /classrooms/<uid>/members/?status=pending|approved"""
        svc = ClassroomMemberService()
        filter_status = request.query_params.get('status')
        if filter_status == 'pending':
            members = svc.get_pending_members(classroom_uid)
        else:
            members = svc.get_members(classroom_uid)
        return Response([self._serialize_member(m) for m in members])

    @action(detail=False, methods=['post'])
    def join(self, request, classroom_uid=None):
        """POST /classrooms/<uid>/members/join/"""
        classroom = Service().find(classroom_uid)
        member = ClassroomMemberService().join(
            classroom_uid=classroom.uid,
            user=request.user,
            role='student',
        )
        ClassroomActivityLogService().log(
            classroom_uid=classroom_uid,
            log_level='detail',
            event_type='member_joined',
            actor_id=request.user.uid,
            actor_name=member.member_name,
            actor_role='student',
            target_name=classroom.name,
        )
        return Response(self._serialize_member(member), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path=r'(?P<member_id>[^/.]+)/approve')
    def approve(self, request, classroom_uid=None, member_id=None):
        """POST /classrooms/<uid>/members/<member_id>/approve/"""
        member = ClassroomMemberService().approve(
            classroom_uid=classroom_uid,
            member_id=member_id,
            approved_by_id=request.user.uid,
        )
        _log = ClassroomActivityLogService()
        _log.log(
            classroom_uid=classroom_uid,
            log_level='major',
            event_type='member_approved',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=member.member_id,
            target_name=member.member_name,
        )
        _log.log(
            classroom_uid=classroom_uid,
            log_level='detail',
            event_type='member_approved',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=member.member_id,
            target_name=member.member_name,
        )
        return Response(self._serialize_member(member), status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path=r'(?P<member_id>[^/.]+)/reject')
    def reject(self, request, classroom_uid=None, member_id=None):
        """DELETE /classrooms/<uid>/members/<member_id>/reject/"""
        ClassroomMemberService().reject(
            classroom_uid=classroom_uid,
            member_id=member_id,
            rejected_by_id=request.user.uid,
        )
        ClassroomActivityLogService().log(
            classroom_uid=classroom_uid,
            log_level='detail',
            event_type='member_rejected',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=member_id,
        )
        return Response({'message': 'Đã từ chối yêu cầu tham gia.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def leave(self, request, classroom_uid=None):
        """POST /classrooms/<uid>/members/leave/"""
        ClassroomMemberService().leave(
            classroom_uid=classroom_uid,
            member_id=request.user.uid,
        )
        ClassroomActivityLogService().log(
            classroom_uid=classroom_uid,
            log_level='detail',
            event_type='member_left',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='student',
        )
        return Response({'message': 'Left successfully'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path=r'(?P<member_id>[^/.]+)/kick')
    def kick(self, request, classroom_uid=None, member_id=None):
        """DELETE /classrooms/<uid>/members/<member_id>/kick/"""
        ClassroomMemberService().kick(
            classroom_uid=classroom_uid,
            member_id=member_id,
            kicked_by_id=request.user.uid,
        )
        ClassroomActivityLogService().log(
            classroom_uid=classroom_uid,
            log_level='detail',
            event_type='member_kicked',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=member_id,
        )
        return Response({'message': 'Kicked successfully'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path=r'(?P<member_id>[^/.]+)/submissions')
    def student_submissions(self, request, classroom_uid=None, member_id=None):
        """GET /classrooms/<uid>/members/<member_id>/submissions/
        Returns all exams in the classroom paired with the student's submission (or null).
        """
        from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
        from features.course.exam.serializers import serialize_exam_submission

        exam_repo = ExamRepository()
        submission_repo = ExamSubmissionRepository()

        exams = list(exam_repo.list_by_classroom(classroom_uid))
        result = []
        for exam in exams:
            submissions = submission_repo.list_by_exam_and_student(exam.uid, member_id)
            sub = submissions[0] if submissions else None
            result.append({
                'exam': {
                    'uid': str(exam.uid),
                    'title': exam.title,
                    'status': exam.status,
                    'due_date': exam.due_date.isoformat() if exam.due_date else None,
                },
                'submission': serialize_exam_submission(sub) if sub else None,
            })
        return Response(result)
