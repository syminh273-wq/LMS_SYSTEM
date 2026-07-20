import logging
from features.course.repositories import (
    CourseRepository,
    CourseLessonRepository,
    CourseEnrollmentRepository,
)
from features.sharing.services import LinkService
from features.sharing.repositories import LinkRepository
from features.sharing.enums import ResourceType
from core.search_engine.typesense.indexer import LMSIndexer

logger = logging.getLogger(__name__)


class CourseService:
    def __init__(self):
        self.repo = CourseRepository()
        self.lesson_repo = CourseLessonRepository()
        self.enrollment_repo = CourseEnrollmentRepository()
        self.link_service = LinkService()
        self.link_repo = LinkRepository()

    def all(self):
        return self.repo.all()

    def find(self, uid):
        return self.repo.find(uid)

    def get_published_courses(self):
        return self.repo.get_published_courses()

    def get_by_teacher(self, teacher_id):
        return self.repo.get_by_teacher(teacher_id)

    def get_by_pid(self, pid):
        return self.repo.get_by_pid(pid)

    def create_course(self, teacher_id, data: dict):
        # Generate unique 6-char code prefixed with K (Khóa học) to avoid collision with classroom codes
        pid = self._generate_unique_course_code()
        course = self.repo.create(teacher_id=teacher_id, pid=pid, **data)

        # Create sharing link for public preview
        self.link_service.create_link({
            'code': pid,
            'resource_type': ResourceType.COURSE.value,
            'resource_id': course.uid,
            'action': 'preview',
            'metadata': {
                'name': course.name,
                'pricing_type': course.pricing_type,
                'price_vnd': str(course.price_vnd or 0),
                'cover_url': course.cover_url or '',
            },
        })

        LMSIndexer.index_course(course)
        return course

    def update(self, instance, **kwargs):
        updated = self.repo.update(instance, **kwargs)
        LMSIndexer.index_course(updated)
        # Update sharing link metadata as well
        try:
            link = self.link_repo.get_by_resource('course', instance.uid).first()
            if link:
                self.link_repo.update(link, metadata={
                    'name': updated.name,
                    'pricing_type': updated.pricing_type,
                    'price_vnd': str(updated.price_vnd or 0),
                    'cover_url': updated.cover_url or '',
                })
        except Exception as e:
            logger.warning(f'[Course] Failed to update link metadata: {e}')
        return updated

    def publish(self, instance):
        # Validate at least 1 published lesson exists
        lessons = list(self.lesson_repo.get_by_course(instance.uid))
        published = [l for l in lessons if l.is_published and not l.is_deleted]
        if not published:
            raise ValueError('Cần ít nhất 1 bài học đã xuất bản trước khi xuất bản khóa học.')
        updated = self.repo.update(instance, status='published')
        LMSIndexer.index_course(updated)
        return updated

    def unpublish(self, instance):
        updated = self.repo.update(instance, status='draft')
        LMSIndexer.index_course(updated)
        return updated

    def delete(self, instance):
        result = self.repo.delete(instance)
        LMSIndexer.remove_course(str(instance.uid))
        return result

    def ensure_classroom(self, course):
        """Auto-create a hidden Classroom on first enrollment. Idempotent."""
        if course.classroom_uid:
            return self._find_classroom(course.classroom_uid)

        from features.course.classroom.services import Service as ClassroomService
        classroom_svc = ClassroomService()
        new_classroom = classroom_svc.create_classroom(
            teacher_id=str(course.teacher_id),
            data={
                'name': course.name,
                'description': f'Lớp học của khóa học: {course.name}',
                'max_students': 0,
                'status': 'active',
            },
        )
        self.repo.update(course, classroom_uid=new_classroom.uid)
        return new_classroom

    def _find_classroom(self, classroom_uid):
        from features.course.classroom.services import Service as ClassroomService
        return ClassroomService().find(str(classroom_uid))

    def get_public_preview(self, code):
        """Resolve code → course → preview lessons. Returns dict for serializer."""
        from rest_framework.exceptions import NotFound
        course = self.get_by_pid(code)
        if not course:
            raise NotFound('Khóa học không tồn tại hoặc đã bị ẩn.')
        if course.status != 'published':
            raise NotFound('Khóa học chưa được xuất bản hoặc đã bị ẩn.')

        preview_lessons = list(self.lesson_repo.get_preview_lessons(course.uid))
        return {
            'course': course,
            'is_free': course.pricing_type == 'free',
            'requires_payment': course.pricing_type == 'paid',
            'preview_lessons': preview_lessons,
        }

    def _generate_unique_course_code(self, max_attempts=10):
        import string
        import random
        for _ in range(max_attempts):
            # 5 random chars + 'K' prefix → total 6 chars, always starts with K
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f'K{random_part}'
            if not self.get_by_pid(code):
                return code
        raise RuntimeError('Failed to generate unique course code after multiple attempts')

    def get_stats(self, course_uid):
        enrollments = list(self.enrollment_repo.list_for_course(course_uid))
        total = len(enrollments)
        paid_total = sum(int(e.amount_vnd or 0) for e in enrollments if e.pricing_type == 'paid')
        return {
            'total_enrollments': total,
            'total_revenue_vnd': paid_total,
            'free_enrollments': sum(1 for e in enrollments if e.pricing_type == 'free'),
            'paid_enrollments': sum(1 for e in enrollments if e.pricing_type == 'paid'),
        }
