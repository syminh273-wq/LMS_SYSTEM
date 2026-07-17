from datetime import datetime, timedelta
from uuid import uuid4

from features.course.exam.repositories import ExamRepository, ExamSessionRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories.exam_audit_log_repository import ExamAuditLogRepository


class ExamSessionService:
    LINK_TTL_MINUTES = 5

    def __init__(self):
        self.session_repo = ExamSessionRepository()
        self.exam_repo = ExamRepository()
        self.member_repo = ClassroomMemberRepository()
        self.audit_repo = ExamAuditLogRepository()

    def open_online(self, exam_uid, teacher_id, late_threshold_seconds=0, duration_seconds=None, camera_required=None, max_face_warnings=None):
        exam = self.exam_repo.get_by_uid(exam_uid)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        if exam.exam_mode != 'online':
            raise ValueError("Exam is not in online mode")

        effective_duration = duration_seconds if duration_seconds is not None else (exam.duration_seconds or 0)
        if not effective_duration or effective_duration <= 0:
            raise ValueError("duration_seconds is required and must be greater than 0 for online exams")

        # Update exam state
        update_data = {
            "is_online_active": True,
            "opened_at": datetime.utcnow(),
            "late_threshold_seconds": late_threshold_seconds,
            "duration_seconds": effective_duration,
            "status": "ongoing",
        }

        if camera_required is not None:
            update_data["camera_required"] = bool(camera_required)

        if max_face_warnings is not None:
            try:
                update_data["max_face_warnings"] = max(0, int(max_face_warnings))
            except (TypeError, ValueError):
                update_data["max_face_warnings"] = 0

        exam = self.exam_repo.update(exam, **update_data)

        members = list(self.member_repo.get_members(classroom_uid=exam.classroom_id))
        students = [m for m in members if m.role == 'student' and not m.is_deleted and m.status == 'approved']
        expires_at = datetime.utcnow() + timedelta(minutes=self.LINK_TTL_MINUTES)

        sessions = []
        for student in students:
            existing = self.session_repo.get_by_student(exam.uid, student.member_id)
            if existing and existing.token_status in ('pending', 'active'):
                # Refresh expiry on pending sessions
                if existing.token_status == 'pending':
                    existing = self.session_repo.update(existing, token_expires_at=expires_at)
                sessions.append(existing)
                continue
            session = self.session_repo.create(
                exam_id=exam.uid,
                student_id=student.member_id,
                token=str(uuid4()).replace('-', ''),
                token_status='pending',
                token_expires_at=expires_at,
            )
            sessions.append(session)
        return sessions, exam

    def close_online(self, exam_uid, teacher_id):
        exam = self.exam_repo.get_by_uid(exam_uid)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        
        # Deactivate exam
        self.exam_repo.update(exam, is_online_active=False, status="closed")
        
        sessions = self.session_repo.list_by_exam(exam_uid)
        for s in sessions:
            if s.token_status == 'pending':
                self.session_repo.update(s, token_status='expired')
        return sessions

    def join(self, token, student_id):
        session = self.session_repo.get_by_token(token)
        if not session:
            raise ValueError("Invalid session token")
        if str(session.student_id) != str(student_id):
            raise ValueError("This session does not belong to you")

        exam = self.exam_repo.get_by_uid(session.exam_id)
        if not exam or not exam.is_online_active:
            raise ValueError("This exam session is not currently open")

        if session.token_status == 'active':
            return session, exam

        if session.token_status != 'pending':
            raise ValueError("Session is no longer valid")

        now = datetime.utcnow()

        # Check late threshold
        if exam.opened_at and exam.late_threshold_seconds > 0:
            diff = (now - exam.opened_at).total_seconds()
            if diff > exam.late_threshold_seconds:
                self.session_repo.update(session, token_status='expired')
                raise ValueError(f"You are late. Entry was only allowed until {exam.late_threshold_seconds // 60} minutes after opening.")

        if session.token_expires_at and now > session.token_expires_at and not exam.is_online_active:
            self.session_repo.update(session, token_status='expired')
            raise ValueError("Session link has expired")

        # Require face enrollment when camera_required
        if exam.camera_required:
            from features.face.models import FaceEmbedding
            embeddings = list(FaceEmbedding.objects.filter(student_id=student_id).allow_filtering())
            if not any(getattr(e, 'is_active', False) for e in embeddings):
                raise ValueError("This exam requires face recognition. Please register your face in your profile first.")

        ends_at = None
        if exam and exam.duration_seconds and exam.duration_seconds > 0:
            ends_at = now + timedelta(seconds=exam.duration_seconds)

        session = self.session_repo.update(session, token_status='active', started_at=now, ends_at=ends_at)

        self.audit_repo.log(
            exam_id=exam.uid,
            student_id=student_id,
            event_type='joined',
            event_data={'started_at': now.isoformat(), 'ends_at': ends_at.isoformat() if ends_at else None},
        )
        return session, exam

    def get_my_session(self, exam_id, student_id):
        session = self.session_repo.get_by_student(exam_id, student_id)
        if session:
            return session

        # No session yet — create one on-the-fly if exam is still active and student is a member
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam or not exam.is_online_active:
            return None
        if not self.member_repo.is_member(exam.classroom_id, student_id):
            return None

        session = self.session_repo.create(
            exam_id=exam.uid,
            student_id=student_id,
            token=str(uuid4()).replace('-', ''),
            token_status='pending',
            token_expires_at=None,
        )
        return session

    def list_by_exam(self, exam_id, teacher_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        return self.session_repo.list_by_exam(exam_id)

    def validate_for_submit(self, exam_id, student_id):
        session = self.session_repo.get_by_student(exam_id, student_id)
        if not session:
            raise ValueError("No active exam session. Please join via your exam link.")
        if session.token_status != 'active':
            raise ValueError("Your exam session is no longer active")
        now = datetime.utcnow()
        # Allow 30s buffer for network latency
        if session.ends_at and now > (session.ends_at + timedelta(seconds=30)):
            self.session_repo.update(session, token_status='expired')
            raise ValueError("Your exam time has expired. Submission is no longer allowed.")
        return session

    def complete(self, exam_id, student_id):
        session = self.session_repo.get_by_student(exam_id, student_id)
        if session and session.token_status == 'active':
            self.session_repo.update(session, token_status='completed')

    def set_submission_effectiveness(self, submission_id, teacher_id, is_effective: bool):
        """
        Teacher bật/tắt `is_effective` cho submission. Cho phép teacher quyết định
        điểm có hiệu lực hay không — kể cả khi student đã bị force_submit.

        Raises:
          ValueError nếu submission không tồn tại hoặc teacher không sở hữu exam.
        """
        from features.course.exam.repositories import ExamSubmissionRepository

        submission_repo = ExamSubmissionRepository()
        submission = submission_repo.get_by_uid(submission_id)
        if not submission:
            raise ValueError("Submission not found")

        exam = self.exam_repo.get_by_uid(submission.exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")

        return submission_repo.update(submission, is_effective=bool(is_effective))
