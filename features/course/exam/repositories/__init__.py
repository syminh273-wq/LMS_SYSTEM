from .exam_repositories import ExamRepository
from .exam_submission_repository import ExamSubmissionRepository
from .exam_session_repository import ExamSessionRepository
from .exam_event_log_repository import ExamEventLogRepository

# Backward-compat alias for old call sites that still import
# `ExamAuditLogRepository`. The class is gone; the name now points to
# the unified ExamEventLogRepository.
ExamAuditLogRepository = ExamEventLogRepository
