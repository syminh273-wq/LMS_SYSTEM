from .classroom_service import ClassroomService
from .classroom_ai_service import ClassroomAIService
from .classroom_doc_service import ClassroomDocService
from .classroom_member_service import ClassroomMemberService
from .classroom_blacklist_service import ClassroomBlacklistService
from .classroom_activity_log_service import ClassroomActivityLogService

Service = ClassroomService  # backward-compat

__all__ = [
    'ClassroomService',
    'ClassroomAIService',
    'ClassroomDocService',
    'ClassroomMemberService',
    'ClassroomBlacklistService',
    'ClassroomActivityLogService',
    'Service',
]
