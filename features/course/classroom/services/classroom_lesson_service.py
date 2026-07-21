from features.course.repositories import CourseLessonRepository
from features.course.classroom.repositories import Repository as ClassroomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository


class ClassroomLessonService:
    """Returns CourseLesson entries for a Classroom, gated by paid status.

    A classroom is paid if `classroom.pricing_type == 'paid'`. A consumer is
    considered a paid member if they have an approved `ClassroomMember` row
    with `has_paid=True`.
    """

    def __init__(self):
        self.classroom_repo = ClassroomRepository()
        self.lesson_repo = CourseLessonRepository()
        self.member_repo = ClassroomMemberRepository()

    def list_lessons(self, classroom_uid, consumer_id=None):
        classroom = self.classroom_repo.find(str(classroom_uid))
        course_uid = getattr(classroom, 'course_uid', None)
        if not course_uid:
            return {
                'classroom': classroom,
                'lessons': [],
                'pricing_type': getattr(classroom, 'pricing_type', 'free'),
                'is_paid_member': False,
                'is_locked': False,
            }

        pricing_type = getattr(classroom, 'pricing_type', 'free') or 'free'

        if pricing_type == 'free':
            lessons = list(self.lesson_repo.get_published_lessons(course_uid))
            return {
                'classroom': classroom,
                'lessons': lessons,
                'pricing_type': pricing_type,
                'is_paid_member': True,
                'is_locked': False,
            }

        is_paid_member = False
        if consumer_id:
            member = self.member_repo.get_paid_member(classroom_uid, consumer_id)
            is_paid_member = member is not None

        if is_paid_member:
            lessons = list(self.lesson_repo.get_published_lessons(course_uid))
            is_locked = False
        else:
            lessons = list(self.lesson_repo.get_preview_lessons(course_uid))
            is_locked = True

        return {
            'classroom': classroom,
            'lessons': lessons,
            'pricing_type': pricing_type,
            'is_paid_member': is_paid_member,
            'is_locked': is_locked,
        }
