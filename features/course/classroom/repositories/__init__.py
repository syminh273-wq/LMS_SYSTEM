from .classroom_repository import ClassroomRepository
from .classroom_member_repository import ClassroomMemberRepository
from .teacher_blacklist_repository import TeacherBlacklistRepository
from .teacher_contact_repository import TeacherContactRepository

Repository = ClassroomRepository  # backward-compat

__all__ = [
    'ClassroomRepository',
    'ClassroomMemberRepository',
    'TeacherBlacklistRepository',
    'TeacherContactRepository',
    'Repository',
]
