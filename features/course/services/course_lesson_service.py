import logging
from features.course.repositories import CourseRepository, CourseLessonRepository

logger = logging.getLogger(__name__)


class CourseLessonService:
    def __init__(self):
        self.course_repo = CourseRepository()
        self.lesson_repo = CourseLessonRepository()

    def list_lessons(self, course_uid, teacher_id=None):
        course = self._verify_course_access(course_uid, teacher_id)
        return list(self.lesson_repo.get_by_course(course.uid))

    def list_preview_lessons(self, course_uid):
        return list(self.lesson_repo.get_preview_lessons(course_uid))

    def list_published_lessons(self, course_uid):
        return list(self.lesson_repo.get_published_lessons(course_uid))

    def get_lesson(self, course_uid, lesson_uid, teacher_id=None):
        course = self._verify_course_access(course_uid, teacher_id)
        lesson = self.lesson_repo.find(lesson_uid)
        if str(lesson.course_uid) != str(course.uid):
            raise PermissionError('Bài học không thuộc khóa học này.')
        return lesson

    def create_lesson(self, course_uid, teacher_id, data: dict):
        from rest_framework.exceptions import PermissionDenied
        course = self.course_repo.find(course_uid)
        if str(course.teacher_id) != str(teacher_id):
            raise PermissionDenied('Bạn không có quyền thêm bài học vào khóa học này.')

        order_index = data.get('order_index')
        if order_index is None:
            order_index = self.lesson_repo.next_order_index(course.uid)

        lesson = self.lesson_repo.create(
            course_uid=course.uid,
            order_index=order_index,
            title=data['title'],
            description=data.get('description', ''),
            video_resource_uid=data.get('video_resource_uid'),
            material_resource_uids=data.get('material_resource_uids', []),
            duration_seconds=data.get('duration_seconds', 0),
            is_preview=data.get('is_preview', False),
            is_published=data.get('is_published', True),
        )
        return lesson

    def update_lesson(self, course_uid, lesson_uid, teacher_id, data: dict):
        from rest_framework.exceptions import PermissionDenied
        course = self.course_repo.find(course_uid)
        if str(course.teacher_id) != str(teacher_id):
            raise PermissionDenied('Bạn không có quyền sửa bài học này.')

        lesson = self.lesson_repo.find(lesson_uid)
        if str(lesson.course_uid) != str(course.uid):
            raise PermissionDenied('Bài học không thuộc khóa học này.')

        update_data = {k: v for k, v in data.items() if v is not None or k in (
            'description', 'video_resource_uid', 'is_preview', 'is_published',
            'duration_seconds', 'order_index',
        )}
        # Drop keys not in the data
        allowed = {'title', 'description', 'video_resource_uid', 'material_resource_uids',
                   'duration_seconds', 'is_preview', 'is_published', 'order_index'}
        update_data = {k: v for k, v in update_data.items() if k in allowed}

        return self.lesson_repo.update(lesson, **update_data)

    def delete_lesson(self, course_uid, lesson_uid, teacher_id):
        from rest_framework.exceptions import PermissionDenied
        course = self.course_repo.find(course_uid)
        if str(course.teacher_id) != str(teacher_id):
            raise PermissionDenied('Bạn không có quyền xóa bài học này.')

        lesson = self.lesson_repo.find(lesson_uid)
        if str(lesson.course_uid) != str(course.uid):
            raise PermissionDenied('Bài học không thuộc khóa học này.')

        return self.lesson_repo.delete(lesson)

    def reorder_lessons(self, course_uid, teacher_id, items: list):
        from rest_framework.exceptions import PermissionDenied
        course = self.course_repo.find(course_uid)
        if str(course.teacher_id) != str(teacher_id):
            raise PermissionDenied('Bạn không có quyền sắp xếp bài học.')

        for idx, item in enumerate(items):
            uid = item.get('uid')
            if not uid:
                continue
            order_index = item.get('order_index', idx)
            lesson = self.lesson_repo.find(uid)
            if str(lesson.course_uid) == str(course.uid):
                self.lesson_repo.update(lesson, order_index=order_index)

        return list(self.lesson_repo.get_by_course(course.uid))

    def _verify_course_access(self, course_uid, teacher_id=None):
        course = self.course_repo.find(course_uid)
        if teacher_id is not None and str(course.teacher_id) != str(teacher_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Bạn không có quyền truy cập khóa học này.')
        return course
