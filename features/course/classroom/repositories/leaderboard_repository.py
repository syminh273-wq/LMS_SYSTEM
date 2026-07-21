from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.calendar.repositories.attendance_repository import AttendanceRepository
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository
from features.quiz.repositories.quiz_attempt_repository import QuizAttemptRepository
from features.quiz.repositories.quiz_log_repository import QuizLogRepository
from features.course.exam.repositories.exam_submission_repository import ExamSubmissionRepository


class LeaderboardRepository:
    """Read-only aggregations for classroom leaderboards. All queries are scoped
    to a single classroom (we use ALLOW FILTERING on tables whose primary key
    does not include classroom_id, since the expected cardinality is small)."""

    def __init__(self):
        self.member_repo = ClassroomMemberRepository()
        self.quiz_attempt_repo = QuizAttemptRepository()
        self.quiz_log_repo = QuizLogRepository()
        self.exam_sub_repo = ExamSubmissionRepository()
        self.event_repo = CalendarEventRepository()
        self.attendance_repo = AttendanceRepository()

    def get_approved_students(self, classroom_id):
        return list(self.member_repo.get_members(classroom_id))

    def iter_quiz_attempts(self, classroom_id):
        return list(self.quiz_attempt_repo.iter_classroom_attempts(classroom_id))

    def iter_quiz_logs(self, classroom_id):
        return list(self.quiz_log_repo.iter_classroom_logs(classroom_id))

    def iter_exam_submissions(self, classroom_id):
        return list(self.exam_sub_repo.iter_by_classroom(classroom_id))

    def list_classroom_events(self, classroom_id):
        return list(self.event_repo.get_by_classroom(classroom_id))

    def count_present(self, user_id, event_ids):
        return self.attendance_repo.count_present_by_user_events(user_id, event_ids)
